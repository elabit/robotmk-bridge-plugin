# INSTRUCTION.md  
## Purpose
This repository describes the **Robotmk-Bridge** agent plugin, a universal integration layer that connects *any* test automation tool to **Robotmk** and ultimately **Checkmk**.  

This instruction file explains the concept, architecture, and development guidelines so that Claude 4.5 can assist in generating documentation, handler templates, or examples consistently.

Whenever "Robotmk-Bridge" or "the Bridge" is mentioned, it refers to this adapter plugin.
However, the official repo name is "robotmk-bridge-plugin".

---

## 1. Concept Overview

The **Robotmk-Bridge** shall act as a **translator** between arbitrary test result formats (e.g., JUnit, Cypress, Playwright, Tosca, Xunit, Postman, REST API tests, etc.), and the format understood by the **Robotmk** (JSON result format, wrapping the Robot framework XML output with other fields.)
Those results are then forwarded to **Checkmk**, where they become visible and monitorable as services.

### Key Idea

> Any test tool → Robot-Bridge → Robotmk JSON result files → Checkmk

### Motivation
- Many teams already have existing test tools and pipelines.  
- The Robotmk Scheduler produces JSON result files which encapsulate the Robot Framework XML output. They are stored on the monitored host and collected by Checkmk agents.
- Robot-Bridge removes the need to rewrite tests in Robot Framework.  
- Each supported test tool simply needs a **handler** that converts its native results into Robot Framework XML. Writing such a handler is not part of this repo.

---

## 2. Architecture

The bridge plugin consists of the following components:

- **Agent Plugin** (stored in agents_plugins): The main Python plugin installed on the Checkmk agent side. It reads test result files from specified paths and invokes the appropriate handler to convert them. After that, with the help of rf-oxygen, it converts the result and creates the Robotmk JSON result in the same way as the original Robotmk Scheduler would do. Even if not all JSON fields make 100% sense for such a passive result, it will be faked for this early POC phase. As the agents_plugins folder only contains the plugin to be deployed to the monitored host, we will install a checkmk agent on the same machine and symlink the plugin from agents_plugins into the agent's plugins folder.
- **Agent PLugin Configuration**: JSON, Configured via Checkmk Bakery rule, specifying paths to test result files and which handler to use for each path.
- **Handlers**: Python modules for the "robotframework-oxygen" package that implement the logic to parse specific test result formats and convert them into Robot Framework XML. Handlers are separate from this repo and need to be developed independently. Later, we will fork this repo to create a dedicated "robotmk-bridge" package for handlers to quickly accept PRs for more handlers coming from the community.
- **Bakery rule**: A Checkmk Bakery rule that allows users to configure the Bridge plugin, specifying paths and handlers. Stored in /bakery
- **Checks**: Even if the results are processed passively for Robotmk on the remote side, there shall be a separate check on the server side to monitor if the conversion of files performs, mesaure conversion times, and report errors if files are missing or malformed. Stored in /checks

---

3. Data to read from 

The paths for the bridge plugin to read from can be arbotrary and are configured via the Bakery rule. Each path must be associated with a specific handler.

4. Output 

The file sample_data/globetrack_simple.json is an example of the final Robotmk JSON result file. It was prouced by the Robotmk scheduler. The Bridge plugin after converting test results should product a similar file, including the Robot Framework XML output.

The Bridge plugin will determine the Robotmk Scheduler folder from the Scheduler COnfig file (JSON). /etc/check_mk/robotmk.json
By default, it is /var/lib/check_mk_agent/robotmk/scheduler/results/plans, followed by the JSON file, named with the plan name. 

5. Typical Workflow

A test tool (e.g., Tosca) produces its native result file(s) in Folder X. 
The user configures the Bakery rule for the Bridge plugin, specifying Folder X and the Tosca type.
He then bake the agent, installs the agent on the monitored host.
The Checkmk agent runs the Bridge plugin during its execution. 

Robot-Bridge reads its JSON config and processes each configured path. 
Path must be a concrete file. 
The Bridge uses the specific handler to parse the test result file, convert it internally to Robot Framework XML format.
It shoudl also use "rebot" to produce a log.html from the XML. 
The Plugin then writes the JSON result file, faking metadata which are not acailable, warpping the RF XML and HTML in the JSON (see example file).


On Checkmk, the results are dicovered as normal Robotmk servcies. 

However, the bridge plugin also produces its own agent section (see https://docs.checkmk.com/latest/en/devel_check_plugins.html?lquery=section#test_agent)
which is used by a dedicated check (stored in /checks) to monitor the Bridge plugin itself.



## Others

The Workspace also contains the devontainer folder /opt/omd/sites/cmk with a running Checkmk site. 

---

## Technology Stack

- devcontainer: 
  - based on Ubuntu 22.04, 
  - python in /usr/bin/python3
  - robotframework-oxygen package installed
- Checkmk 2.4 with its own python interpreter (/omd/sites/cmk/bin/python3)

---

## Further ideas


- Result merging: optionally, use "rebot" internally on the bridge plugin to merge multiple test result files into one Robot Framework XML before wrapping it into Robotmk JSON.