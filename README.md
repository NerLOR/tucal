
# TUcal – a unified calendar for TU Wien

## Setup own instance

1. Copy `tucal.default.ini` to `tucal.ini` and update values.
2. To initialize database run
    ```shell
    make database
    ```
3. To deploy run
    ```shell
    tools/deploy.sh <hostname> <path>
    ```
    or to build only run
    ```shell
    make build-www
    ```