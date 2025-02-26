# FossID Workbench API Examples!
These scripts were built by the FossID Customer Experience teams in collaboration with Engineering to solve specific use cases raised by customers via the [FossID Support Portal](https://support.fossid.com/). 

### Supportability
These examples demonstrate how to interact with the Workbench API. We do our best to keep the examples updated, but there is no long-term maintainer for this code. We do not use GitHub Issues - for questions or issues with the scripts please use the [FossID Support Portal](https://support.fossid.com/). Thank you! 

## Example Scripts
Each script interacts with the FOSSID workbench API. To use our API a payload dictionary is required for each API call.
Each different API call has a different payload with different requirments. To see these requirements, you can look in the
scripts to see each required key for the payload or view it on API website.

The repo has scripts that help you:

### Archive Old Scans
This script helps clients archive stale scans based on when they were last modified.

### Post Scan Gates
This script checks scans for Pending Identifications and Policy Violations - useful for gating CI/CD pipelines.

### Post Scan Reports
This script downloads reports for a scan - useful if you want to include FossID reports as build artifacts.

### Quickly Scan a File
This script scans a single file using the Quick Scan API - helpful for quickly knowing if AI-generated code should be investigated further.

### Helper Functions
This script contains helper functions that are used in the example scripts

## Contributing
Contributions are welcome! We'll review any Pull Requests made.

