use std::io::{Read, Write};
use std::net::{TcpListener, TcpStream};
use std::sync::Mutex;
use std::thread;
use std::time::Duration;
use tauri::{webview::WebviewWindowBuilder, Manager, RunEvent, WebviewUrl};
use tauri_plugin_shell::{process::CommandChild, ShellExt};

fn available_port() -> std::io::Result<u16> {
    let listener = TcpListener::bind("127.0.0.1:0")?;
    Ok(listener.local_addr()?.port())
}

fn server_ready(port: u16) -> bool {
    let address = ([127, 0, 0, 1], port).into();
    let Ok(mut stream) = TcpStream::connect_timeout(&address, Duration::from_millis(150)) else {
        return false;
    };
    let _ = stream.set_read_timeout(Some(Duration::from_millis(200)));
    if stream
        .write_all(b"GET /api/health HTTP/1.0\r\nHost: 127.0.0.1\r\n\r\n")
        .is_err()
    {
        return false;
    }
    let mut response = [0; 128];
    matches!(stream.read(&mut response), Ok(n) if response[..n].starts_with(b"HTTP/1.1 200") || response[..n].starts_with(b"HTTP/1.0 200"))
}

fn main() {
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            let port = available_port()?;
            let command =
                app.shell()
                    .sidecar("vengine-server")?
                    .args(["serve", "--port", &port.to_string()]);
            let (_rx, child) = command.spawn()?;
            let mut child = Some(child);
            for _ in 0..100 {
                if server_ready(port) {
                    break;
                }
                thread::sleep(Duration::from_millis(100));
            }
            if !server_ready(port) {
                if let Some(child) = child.take() {
                    let _ = child.kill();
                }
                return Err("V-engine server did not start within 10 seconds".into());
            }
            let url = format!("http://127.0.0.1:{port}").parse()?;
            if let Err(error) = WebviewWindowBuilder::new(app, "main", WebviewUrl::External(url))
                .title("V-engine")
                .inner_size(1180.0, 780.0)
                .min_inner_size(640.0, 500.0)
                .build()
            {
                if let Some(child) = child.take() {
                    let _ = child.kill();
                }
                return Err(error.into());
            }
            app.manage(Mutex::new(child));
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("failed to build V-engine desktop");
    app.run(|handle, event| {
        if let RunEvent::Exit = event {
            if let Some(state) = handle.try_state::<Mutex<Option<CommandChild>>>() {
                if let Ok(mut guard) = state.lock() {
                    if let Some(child) = guard.take() {
                        let _ = child.kill();
                    }
                }
            }
        }
    });
}
