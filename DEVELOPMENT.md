# Development

This page explains step by step how to set up your development environment to debug and develop Robotmk.  
Feel encouraged to contribute code!

## Preconditions

* Docker
* Visual Studio Code (Devcontainer Setup)

### Build Devcontainer images

Open `.devcontainer/devcontainer_img_versions.env` and add all versions of Checkmk you want to develop on to the `CMKVERSIONS` variable. (= All versions are a long quoted string, separated by newlines.)

Example:

     CMKVERSIONS="2.4.0p12
     2.3.0p37
     2.2.0p32"

After that, run the following command to build the required Docker images:

    .devcontainer/scripts/devcontainer_img_build.sh

What it does: 

* First it checks if the CMK Docker images are already available locally. If not, it connects to the [Checkmk Docker Registry](registry.checkmk.com) and downloads the images from there.
* It then creates a new Docker image based on the CMK docker image (downloaded in step 1) and installs some more things (see `.devcontainer/Dockerfile_cmk_py3_dev`):
  * Python modules form `.devcontainer/requirements.txt`
  * some additional tools: `jq tree htop vim git telnet file ...`
* For each version it creates an image `cmk-python3-dev:VERSION`.

The devcontainers are started based on these images, depending on `${VARIANT}`.
See `.devcontainer/Dockerfile` (which is referenced in `devcontainer.json`):

---

### Generate devcontainer.json

You can always work on 1 CMK container at the same time.
To generate the version-specific devcontainer JSON file, execute the following command:

    .devcontainer/scripts/devcontainer_gen.sh VERSION

```bash
bash .devcontainer/scripts/devcontainer_gen.sh
No cmk version (arg1) specified. Select a version:
1) 2.4.0p12
2) 2.3.0p37
3) 2.2.0p32
#? 1
Selected version: 2.4.0p12
+ Generating CMK devcontainer file ...
```

What it does: It reconfigures `.devcontainer/devcontainer.json` using `envsubst` and the template file in `.devcontainer/devcontainer_tpl.json`

### Choose and Start the Checkmk devcontainer

Start the container with *Cmd-Shift-P* > select `Remote-Containers: Rebuild Container`.

What it does: 

- Starts the devcontainer & Checkmk Site
- All project relevant files get symlinked by `.devcontainer/linkfiles.sh` into the devcontainer.
- At the end, you are asked to start the interactive creation of a dummyhost. 

The devcontainer is ready now. Open the Checmk login page on <http://127.0.0.1:4999>.

---

## How to develop

### Add CMK site to workspace

VS code displays by default only the files of the workspace (`/workspaces/robotmk`). They are symlinked to the OMD site, but if you want to debug, you have to add `$OMD_ROOT` as another folder to the workspace:

![](./img/vs_code_add_folder.png)

You can now add breakpoints to the scripts in this folder to debug them.  
Also, only then the code completion (classes, functions, ...) works properly, because it works in the same Python context as Checkmk.


### Commit workflow

This project uses [release please](https://github.com/googleapis/release-please-action) to maintain the Changelog and Releases. 

Resources: 

- https://elixirschool.com/blog/managing-releases-with-release-please
- https://github.com/googleapis/release-please/blob/main/docs/manifest-releaser.md
- https://medium.com/@nicolaslelievre/automating-dbt-package-versioning-with-release-please-97ebe0ce9809

Notes: 

- Use feature branches
- Write commit messages which follow the [https://www.conventionalcommits.org/en/v1.0.0/]{Conventional Commit Standard}
  - `fix(bridge)`: correct xml escaping => patch
  - `feat(gatling)`: aggregate requests per scenario => minor
  - `chore(ci)`: speed up mkp packaging => major
- push to feature branch 
- create PR, merge to main
- RP creates Release PR => merge => Release is created
- Run the MKP workflow (currently not possible to run after the Release workflow) => MKPs are built and added to the release. 


## Others

### Bash'ing into the container

VS Code already presents you a bash terminal as user `cmk`.
In Order to open another bash as `root`, just execute `docker exec -it rmk-dev bash`

Inside of the `root` bash, you can also open a preconfigured `tmux` terminal which allows to work with multiple panes.
Shortcuts ("Ca" = Ctrl + a):

* Split horizontaly: `Ca + -`
* Split vertically: `Ca + |`
* Change focus to other pane: `Ca + [arrow]` ([arrow] = Cursor keys)
* Toggle full screen: `Ca + z`
* Toggle Scroll: `Ca + [` => Page up/down => Ctrl+c to quit scrollmode

### Bash conveniences

| user | alias source              | from                         | linked by                            |
| ---- | ------------------------- | ---------------------------- | ------------------------------------ |
| cmk  | `$OMD_ROOT/.bash_aliases` | `scripts/.site_bash_aliases` | `.devcontainer/scripts/linkfiles.sh` |
| root | `/root/.bash_aliases`     | `scripts/.root_bash_aliases` | `.devcontainer/Dockerfile`           |


### Apply changes

After you have changed a Checkmk file (Bakery, Check, etc), certain actions need to be taken to apply the changes: 

- Bakery: 
  - `omd restart` - To make the rule searchable in the menu
  - `omd reload apachge` - after content changes