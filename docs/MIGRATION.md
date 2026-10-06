# Migration to the package-backed project

Projects generated before 0.2.0 included a copied `vengine/` source tree. Keep a backup of the whole project, including its private data, before migration.

1. Install the new `vengine` package in the project environment. Until publication, install the current checkout in editable mode.
2. Compare your copied engine code with the former version and move project-specific changes into `project_plugins.py` using the documented parser, proposer, AI provider, or grader hooks. Custom browser controls need a separate implementation review because no public renderer hook exists yet.
3. Create `vengine.toml` with `vengine --project . init`, or open `vengine --project . serve` and save the Project view.
4. Move private source files and `project.sqlite3` into `data/` if they lived elsewhere. Start the server once; schema migration creates a `*.pre-v3.bak` backup before adding page checkpoints.
5. Check review drafts, published exercises, attempts, and source links in the browser. Remove the copied `vengine/` tree only after imports resolve to the installed package and the data has been verified.

The old `--data` CLI path remains available for direct use of an existing data directory. Version 0.3 adds shared passage storage (`user_version=4`) and creates a `*.pre-v4.bak` backup when opening an existing v3 database. Do not commit the private `data/` directory or database backups.
