import click
import requests
import json
import time
import os
import os.path


REPORT_TYPE = ("html", "dynamic_top_matched_components", "xlsx", "spdx", "spdx_lite", "cyclone_dx", "string_match")
SELECTION_TYPE = ("include_all_licenses", "include_foss", "include_marked_licenses", "include_copyleft")
SELECTION_VIEW = ("all", "pending_identification", "marked_as_identified")
TYPE_TRANSLATION = {
    "dynamic": "html",
    "xlsx": "xlsx",
    "spdx": "rdf",
    "dynamic_top_matched_components": "html",
    "string_match": "xlsx",
    "spdx_lite": "xlsx",
    "cyclone_dx": "json",
    "html": "html"
}


class APIException(Exception):
    pass


class ScanNotFoundException(APIException):
    pass


def get_scan_status(host, username, key, scan_code, queue_id=None):
    """
    Get scan status from Workbench API: scans.check_status

    :param host: Workbench API URL
    :type host: str
    :param username: Username
    :type username: str
    :param key: API user token
    :type key: str
    :param scan_code: Scan code
    :type scan_code: str
    :param queue_id: Queue ID
    :type queue_id: str
    :return: Dictionary with scan info
    :rtype: dict
    """
    if queue_id:
        payload = {
        "group": "scans",
        "action": "check_status",
        "data": {
            "username": username,
            "key": key,
            "scan_code": scan_code,
            "delay_response": "1",
            "process_id": queue_id,
            "type": 'REPORT_GENERATION'
        }
    }
    else:
        payload = {
        "group": "scans",
        "action": "check_status",
        "data": {
            "username": username,
            "key": key,
            "scan_code": scan_code,
            "delay_response": "1"
        }
    }
    response = requests.post(host, json.dumps(payload), timeout=10)
    results = json.loads(response.text)
    # Validate scan status
    if results["status"] == "1":
        scan_status = results.get("data")
        if queue_id:
            print(f"Progress state : {scan_status['progress_state']}")
            is_finished = (
                    scan_status.get("progress_state") == "FAILED" or
                    scan_status.get("progress_state") == "FINISHED"
            )
            if is_finished:
                return scan_status
            else:
                return dict()
        else:
            is_finished = (
                    scan_status.get("is_finished") or
                    scan_status.get("is_finished") == "1" or
                    scan_status.get("status") == "FAILED" or
                    scan_status.get("status") == "FINISHED"
            )
            if is_finished:
                return scan_status
            else:
                return dict()

    if results["status"] == "0":
        if results.get("error") == "Classes.TableRepository.row_not_found":
            raise ScanNotFoundException("Scan code not found!")
        else:
            raise APIException("Not able to connect to API, check your credentials and try again")
    else:
        return dict()


def download_report(username, key, report_type, api_server, queue_id, use_download_group=False, debug=False):
    """
    Download report

    :param username: Username
    :type username: str
    :param key: API user token
    :type key: str
    :param api_server: Workbench API URL
    :type api_server: str
    :param report_type: Report type
    :type report_type: str
    :param process_id: Queue ID
    :type process_id: str
    :param use_download_group: Use download group when saving reports. This is for Workbench 23+
    :type use_download_group: bool
    :param debug: bool
    :return: Report bytes
    :rtype: bytearray
    """
    data = {
        "group": "download",
        "action": "download_report",
        "data": {
            "username": username,
            "key": key,
            "report_entity": "scans",
            "process_id": queue_id
        }
    }
    if debug:
        print("SENT REQUEST FOR REPORT:")
        print(data)
    response = requests.post(api_server, data=json.dumps(data, indent=4), timeout=120)
    bytes_response = bytes()
    for chunk in response.iter_content(chunk_size=None):
        bytes_response = bytes_response + chunk
    return bytes_response


def generate_report(host, username, key, scan_code, report_type=REPORT_TYPE[0], selection_type=SELECTION_TYPE[0],
                    selection_view=SELECTION_VIEW[0], disclaimer="", use_download_group=False, debug=False):
    """
    Generate report

    :param host: Workbench API URL
    :type host: str
    :param username: Username
    :type username: str
    :param key: API user token
    :type key: str
    :param scan_code: Scan code
    :type scan_code: str
    :param report_type: Report type
    :type report_type: str
    :param selection_type: Selection type
    :type selection_type: str
    :param selection_view: Selection view
    :type selection_view: str
    :param disclaimer: Disclaimer text
    :type disclaimer: str
    :param use_download_group: Use download group when downloading report. Used in version 23+
    :type use_download_group: bool
    :param debug: Debug mode
    :type debug: bool
    :return: Report
    :rtype: bytearray
    """
    # Validate report type
    if report_type:
        if not report_type.lower() in REPORT_TYPE:
            click.secho(
                f"Report type {report_type} is not supported! Generating with default value: {REPORT_TYPE[0]}:",
                bold=True
            )
    # Validate selection type
    if selection_type:
        if not selection_type.lower() in SELECTION_TYPE:
            click.secho(
                f"Report type {selection_type} is not supported! Generating with default value: {SELECTION_TYPE[0]}:",
                bold=True
            )
    data = {
        "username": username,
        "key": key,
        "scan_code": scan_code,
        "report_type": report_type,
        "selection_type": selection_type,
        "async": "1" if report_type in ["xlsx", "spdx", "cyclone_dx", "spdx_lite"] else "0"
        # ("html", "dynamic_top_matched_components", "xlsx", "spdx", "spdx_lite", "cyclone_dx", "string_match")
    }
    if debug:
        print("SENT REQUEST FOR REPORT:")
        print(json.dumps(data, indent=4))
    if selection_view:
        data["selection_view"] = selection_view
    if disclaimer:
        data["disclaimer"] = disclaimer
    # Create request body
    response = requests.post(
        host,
        data=json.dumps(
            {
                "group": "scans",
                "action": "generate_report",
                "data": data
            }
        ))
    try:
        json_response = response.json()
        _status = json_response.get("status")
        if debug:
            print("SENT REQUEST TO GENERATE REPORT:")
            print(json.dumps(json_response, indent=4))
        if _status == "0":
            raise APIException(f"Error trying to get scan info for {scan_code}!") from Exception
        _data = json_response.get("data")
        if not _data:
            raise APIException(f"No data available for scan: {scan_code}") from Exception
        queue_id = _data.get("process_queue_id")
        if debug:
            print(f"GOT process_queue_id: {queue_id}")
        if not queue_id:
            generation_process = _data.get("generation_process")
            if generation_process:
                queue_id = generation_process.get("id")
                if not queue_id:
                    raise APIException(f"No process_queue_id available for scan: {scan_code}") from Exception
            else:
                raise APIException(f"No process_queue_id available for scan: {scan_code}") from Exception

        scan_not_finished = True
        while scan_not_finished:
            scan_status = get_scan_status(host=host, username=username, key=key, scan_code=scan_code, queue_id=queue_id)
            if debug:
                print(json.dumps({scan_code: scan_status}, indent=4))
            if scan_status.get('progress_state') is not None:
                progress_state = scan_status.get("progress_state", str())
                if progress_state != 'FINISHED':
                    raise APIException(f"Report was not generated successfully, status: {progress_state}") from Exception
                elif progress_state == "FINISHED":
                    break
            time.sleep(5)
        return download_report(username=username, key=key, report_type=report_type, api_server=host, queue_id=queue_id, use_download_group=use_download_group, debug=debug)
    except requests.exceptions.JSONDecodeError:
        json_response = dict()
    if not json_response:
        try:
            res = bytes()
            for chunk in response.iter_content(chunk_size=None):
                res = res + chunk
            return res
        except Exception as e:
            raise APIException("Not able to connect to API!") from e
    else:
        raise APIException("Error trying to get scan info!") from Exception


@click.group()
@click.option("--host", help="Webapp URL including api endpoint", default=None)
@click.option("--username", help="Webapp URL including api endpoint", default=None)
@click.option("--key", help="Webapp URL including api endpoint", default=None)
@click.pass_context
def cli(ctx, host, username, key):
    """
    Generate Report When Scan is Ready
    """
    ctx.ensure_object(dict)
    ctx.obj["host"] = host
    ctx.obj["username"] = username
    ctx.obj["key"] = key
    pass


@cli.command("generate")
@click.argument("scan_code", type=str)
@click.option("--use_download_group", type=bool, is_flag=True)
@click.option("--debug", type=bool, is_flag=True)
@click.option("--output_file", type=click.File("wb"))
@click.option("--report_type", type=click.Choice(REPORT_TYPE), default=REPORT_TYPE[0])
@click.option("--selection_type", type=click.Choice(SELECTION_TYPE), default=SELECTION_TYPE[0])
@click.option("--selection_view", type=click.Choice(SELECTION_VIEW), default=SELECTION_VIEW[0])
@click.option("--disclaimer", type=str, default=None)
@click.pass_context
def generate(ctx, scan_code, output_file=None, report_type=None, selection_type=None, selection_view=None,
             disclaimer=None, use_download_group=False, debug=False):
    """
    Generate Report
    """
    host = ctx.obj["host"]
    if not host:
        host = click.prompt("Enter WebApp url including api endpoint", type=str)

    username = ctx.obj["username"]
    if not username:
        username = click.prompt("Enter WebApp username", type=str)

    key = ctx.obj["key"]
    if not key:
        key = click.prompt(f"Enter WebApp api key for user {username}", type=str)

    completed = False
    while not completed:
        click.clear()
        click.secho(f"Checking scan status for {scan_code}", bold=True)
        try:
            results = get_scan_status(host, username, key, scan_code)
            if results:
                completed = results.get("is_finished")
                if completed:
                    click.secho(f"Scan status for {scan_code} is: {results.get('status')}", fg="green")
                else:
                    click.echo(f"Scan status: {results.get('status')}")
                    click.echo(f"Percentage: {results.get('percentage_done')}")
                    click.echo(f"Total files: {results.get('total_files')}")
                    click.echo(f"Ignored files: {results.get('ignored_files')}")
                    click.echo(f"Failed files: {results.get('failed_files')}")
            if not completed:
                time.sleep(3)
        except APIException as e:
            click.secho(e, fg="red", bold=True)
            exit()

    if not output_file:
        output_file = click.prompt("Please enter path to output file", type=click.File('wb'))
    # Validate output file name
    if output_file:
        file_name = output_file.name
        report_extension = TYPE_TRANSLATION.get(report_type)
        if os.path.isdir(file_name):
            file_name = os.path.join(file_name, f"{scan_code.replace('.', '_')}.{report_extension}")
            output_file.name = file_name
        else:
            file_extension = file_name.split(".")[-1]
            if len(file_name.split(".")) == 1:
                file_name = f"{file_name}.{report_extension}"
                output_file.name = file_name
            elif not file_name.endswith(report_extension):
                file_name = file_name.replace(file_extension, report_extension)
                output_file.name = file_name
    # Generate report
    click.secho(f"Generating report for {scan_code}", bold=True)
    report = generate_report(
        host=host,
        username=username,
        key=key,
        scan_code=scan_code,
        report_type=report_type,
        selection_type=selection_type,
        selection_view=selection_view,
        disclaimer=disclaimer,
        use_download_group=use_download_group,
        debug=debug
    )
    output_file.write(report)
    click.secho(f"Finished generating report and saved it in: {output_file.name}", fg="green", bold=True)


if __name__ == '__main__':
    cli()
