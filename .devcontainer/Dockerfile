# See here for image contents: https://github.com/microsoft/vscode-dev-containers/tree/v0.155.1/containers/ubuntu/.devcontainer/base.Dockerfile

ARG VARIANT
# Build the dev images with .devcontainer/build-devcontainer.sh !
# See https://stackoverflow.com/a/69798220 to run the image on Apple M1
# FROM --platform=linux/amd64 cmk-python3-dev:2.4.0p12
# FROM --platform=linux/amd64 cmk-python-dev:${VARIANT}
FROM cmk-python3-dev:${VARIANT}


ENV CMK_PASSWORD="cmk"

# Creates the OMD site, executes post-start hook and halts before site start
COPY docker-entrypoint.d /docker-entrypoint.d
RUN /docker-entrypoint.sh /bin/true

# make the agent dir writeable from the CMK site (to link RF example tests) 
RUN chgrp -R cmk /usr/lib/check_mk_agent && chmod g+w /usr/lib/check_mk_agent

# Allow cmk user to use sudo
RUN apt-get update && apt-get install -y sudo \
    && echo "cmk ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers.d/cmk \
    && chmod 0440 /etc/sudoers.d/cmk

ENTRYPOINT ["/bin/bash"]