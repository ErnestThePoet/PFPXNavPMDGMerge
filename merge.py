import geopy.distance


def dict_append(dict_: dict[any, list[any]], key: any, val: any):
    if key in dict_:
        dict_[key].append(val)
    else:
        dict_[key] = [val]


def to_pmdg_lat(pfpx_lat: str) -> str:
    if len(pfpx_lat) != 9:
        raise ValueError(f"pfpx_lat {pfpx_lat} is not of length 9")

    return f"{int(pfpx_lat[:3])}.{pfpx_lat[3:9]}"


def to_pmdg_lon(pfpx_lon: str) -> str:
    if len(pfpx_lon) != 10:
        raise ValueError(f"pfpx_lon {pfpx_lon} is not of length 10")

    return f"{int(pfpx_lon[:4])}.{pfpx_lon[4:10]}"


def to_pmdg_elev(pfpx_elev: str) -> str:
    if len(pfpx_elev) != 6:
        raise ValueError(f"pfpx_elev {pfpx_elev} is not of length 6")

    if pfpx_elev.startswith("+"):
        return pfpx_elev.lstrip("+")
    else:
        return f"-{pfpx_elev[2:6]}"


def to_pmdg_freq(pfpx_freq: str, navaid_type: str) -> str:
    if len(pfpx_freq) != 5:
        raise ValueError(f"pfpx_freq {pfpx_freq} is not of length 5")

    if navaid_type == "NDB":
        return f"{int(pfpx_freq[:-1]):.02f}"
    else:
        return f"{pfpx_freq[:3]}.{pfpx_freq[3:5]}"


def read_pfpx_database():
    with open("./PFPX/decoded.nav", "r") as fin:
        lines = fin.read().splitlines(keepends=False)

        # Maps airport ICAO code to runway info list
        icao_runways_map: dict[str, list[dict[str, str]]] = {}

        # Maps ID to PFPX 'waypoint'(airport/waypoint/navaid)
        id_point_map: dict[str, dict[str, str]] = {}

        # Maps airport ICAO to airport data
        icao_airport_map: dict[str, dict[str, str]] = {}

        waypoints: list[dict[str, str]] = []
        navaids: list[dict[str, str]] = []

        # Maps airway code to waypoint info list
        airways: dict[str, list[dict[str, str]]] = {}

        for line in lines:
            line = line.strip()
            if line == "":
                continue

            line_type = line[:3]

            if line_type == "RWY":
                dict_append(icao_runways_map, line[4:8], {
                    "number": line[8:13].strip(),
                    "length": line[13:18],
                    "heading": line[21:24],
                    "lat": to_pmdg_lat(line[27:36]),
                    "lon": to_pmdg_lon(line[36:46])
                })
            elif line_type == "WPT":
                wpt_type = line[12:13]
                wpt_id = line[55:61]

                wpt_lat = to_pmdg_lat(line[66:75])
                wpt_lon = to_pmdg_lon(line[75:85])
                wpt_elev = to_pmdg_elev(line[85:91])

                # Airport
                if wpt_type == "0":
                    airport_code = line[4:8]
                    airport = {
                        "type": "APT",
                        "code": airport_code,
                        "name": line[25:55].strip(),
                        "lat": wpt_lat,
                        "lon": wpt_lon,
                        "elev": wpt_elev
                    }

                    id_point_map[wpt_id] = airport
                    icao_airport_map[airport_code] = airport

                # Waypoint, VFR Waypoint
                elif wpt_type == "6" or (wpt_type == "1" and line[61:66].isspace()):
                    waypoint = {
                        "type": "WPT",
                        "code": line[4:12].strip(),
                        "lat": wpt_lat,
                        "lon": wpt_lon
                    }

                    id_point_map[wpt_id] = waypoint
                    waypoints.append(waypoint)

                # VOR, TACAN, VORTAC, VOR/DME, NDB, DME
                elif wpt_type in ("1", "2", "3", "4", "5", "9"):
                    if line[61:66].isspace():
                        print(f"Navaid with no frequency, ignored:\n{line}")
                        continue

                    pmdg_navaid_type_map = {
                        "1": "VOR",
                        "2": "VOR",
                        "3": "DME",
                        "4": "VORD",
                        "5": "NDB",
                        "9": "DME"
                    }

                    navaid = {
                        "type": pmdg_navaid_type_map[wpt_type],
                        "code": line[4:12].strip(),
                        "name": line[25:55].strip(),
                        "freq": to_pmdg_freq(line[61:66], pmdg_navaid_type_map[wpt_type]),
                        "lat": wpt_lat,
                        "lon": wpt_lon
                    }

                    id_point_map[wpt_id] = navaid
                    navaids.append(navaid)

                else:
                    print(f"Unknown WPT type {wpt_type}")
            elif line_type == "AWY":
                dict_append(airways, line[4:10].strip(), {
                    "start_wpt": line[13:19],
                    "end_wpt": line[19:25],
                    "start_lat": to_pmdg_lat(line[26:35]),
                    "start_lon": to_pmdg_lon(line[35:45]),
                    "end_lat": to_pmdg_lat(line[45:54]),
                    "end_lon": to_pmdg_lon(line[54:64])
                })

        return icao_runways_map, id_point_map, icao_airport_map, waypoints, navaids, airways


def apply_airway_coords():
    for airway_code in airways:
        airway = airways[airway_code]

        for edge in airway:
            if edge["start_wpt"] in id_point_map:
                point = id_point_map[edge["start_wpt"]]

                if edge["start_lat"] != point["lat"]:
                    point["lat"] = edge["start_lat"]

                if edge["start_lon"] != point["lon"]:
                    point["lon"] = edge["start_lon"]

            if edge["end_wpt"] in id_point_map:
                point = id_point_map[edge["end_wpt"]]

                if edge["end_lat"] != point["lat"]:
                    point["lat"] = edge["end_lat"]

                if edge["end_lon"] != point["lon"]:
                    point["lon"] = edge["end_lon"]


def merge_airports_apt():
    with open("./PMDG/airports.dat", "r") as fin:
        lines = list(filter(lambda x: x != "" and not x.startswith(";"), fin.readlines()))

    existing_airport_icaos = set(line[:4] for line in lines)

    new_airport_icaos = []

    for icao in icao_airport_map:
        if icao in existing_airport_icaos:
            continue

        airport = icao_airport_map[icao]
        lines.append(
            f"{airport['code']}{airport['lat']:>10s}{airport['lon']:>11s}\n"
        )
        new_airport_icaos.append(airport["code"])

    with open("merged/airports.dat", "w") as fout:
        fout.writelines(lines)

    with open("./PMDG/wpNavAPT.txt", "r") as fin:
        apt_lines = list(filter(lambda x: x != "" and not x.startswith(";"), fin.readlines()))

    for icao in new_airport_icaos:
        if icao not in icao_runways_map:
            print(f"New airport {icao} has no associated runway data")
            continue

        for runway in icao_runways_map[icao]:
            apt_lines.append(
                f"{icao_airport_map[icao]['name'][:24]:<24s}{icao}{runway['number']:<3s}"
                f"{runway['length']}{runway['heading']}"
                f"{runway['lat']:>10s}{runway['lon']:>11s}"
                f"000.00{runway['heading']}{icao_airport_map[icao]['elev']}\n"
            )

    with open("merged/wpNavAPT.txt", "w") as fout:
        fout.writelines(apt_lines)


def merge_fix(use_pfpx_coords: bool = True):
    with open("./PMDG/wpNavFIX.txt", "r") as fin:
        lines = list(filter(lambda x: x != "" and not x.startswith(";"), fin.readlines()))

    existing_wpts: dict[str, list[tuple[int, float, float]]] = {}

    for line_index, line in enumerate(lines):
        dict_append(
            existing_wpts, line[:24].strip(), (line_index, float(line[29:39]), float(line[39:50])))

    for waypoint in waypoints:
        if waypoint["code"] in existing_wpts:
            already_existing = False
            existing_line_index = -1
            for existing_wpt in existing_wpts[waypoint["code"]]:
                if geopy.distance.distance(
                        (existing_wpt[1], existing_wpt[2]),
                        (float(waypoint["lat"]), float(waypoint["lon"]))).nautical <= 2:
                    already_existing = True
                    existing_line_index = existing_wpt[0]
                    break

            if already_existing:
                if use_pfpx_coords:
                    existing_line = lines[existing_line_index]
                    if existing_line[29:39].strip() != waypoint["lat"] or \
                            existing_line[39:50].strip() != waypoint["lon"]:
                        lines[existing_line_index] = \
                            f"{existing_line[:29]}" \
                            f"{waypoint['lat']:>10s}{waypoint['lon']:>11s}\n"
                continue

        lines.append(
            f"{waypoint['code']:<24s}{waypoint['code']:<5s}"
            f"{waypoint['lat']:>10s}{waypoint['lon']:>11s}\n"
        )

    with open("merged/wpNavFIX.txt", "w") as fout:
        fout.writelines(lines)


def merge_aid(use_pfpx_coords: bool = True):
    with open("./PMDG/wpNavAID.txt", "r") as fin:
        lines = list(filter(lambda x: x != "" and not x.startswith(";"), fin.readlines()))

    existing_navaids: dict[str, list[tuple[int, str, float, float]]] = {}

    for line_index, line in enumerate(lines):
        # Only check VORD/VOR/DME/NDBs
        navaid_type = line[29:33].strip()
        if navaid_type not in ("VORD", "VOR", "DME", "NDB"):
            continue

        dict_append(existing_navaids, line[24:29].strip(),
                    (line_index, navaid_type, float(line[33:43]), float(line[43:54])))

    for navaid in navaids:
        if navaid["code"] in existing_navaids:
            already_existing = False
            existing_line_index = -1
            for existing_navaid in existing_navaids[navaid["code"]]:
                if navaid["type"] == existing_navaid[1] and \
                        geopy.distance.distance(
                            (existing_navaid[2], existing_navaid[3]),
                            (float(navaid["lat"]), float(navaid["lon"]))).nautical <= 2:
                    already_existing = True
                    existing_line_index = existing_navaid[0]
                    break

            if already_existing:
                if use_pfpx_coords:
                    existing_line = lines[existing_line_index]

                    if existing_line[33:43].strip() != navaid["lat"] or \
                            existing_line[43:54].strip() != navaid["lon"]:
                        lines[existing_line_index] = \
                            f"{existing_line[:33]}" \
                            f"{navaid['lat']:>10s}{navaid['lon']:>11s}" \
                            f"{existing_line[54:]}"
                continue

        lines.append(
            f"{navaid['name'][:24]:<24s}{navaid['code']:<5s}{navaid['type']:<4s}"
            f"{navaid['lat']:>10s}{navaid['lon']:>11s}{navaid['freq']}"
            f"{'N' if navaid['type'] == 'NDB' else 'H'}\n"
        )

    with open("merged/wpNavAID.txt", "w") as fout:
        fout.writelines(lines)


def recreate_rte():
    result_lines = []

    for airway_code in airways:
        airway = airways[airway_code]
        # Topo sort
        indegrees: dict[str, int] = {}
        graph: dict[str, list[str]] = {}

        wpts: dict[str, tuple[str, str]] = {}

        for edge in airway:
            wpts[edge["start_wpt"]] = (edge["start_lat"], edge["start_lon"])
            wpts[edge["end_wpt"]] = (edge["end_lat"], edge["end_lon"])

            if (end_wpt := edge["end_wpt"]) in indegrees:
                indegrees[end_wpt] += 1
            else:
                indegrees[end_wpt] = 1

            if (start_wpt := edge["start_wpt"]) in graph:
                graph[start_wpt].append(end_wpt)
            else:
                graph[start_wpt] = [end_wpt]

        topo_stack = []

        for wpt in wpts:
            if wpt not in indegrees:
                topo_stack.append(wpt)

        current_number = 1
        while len(topo_stack) > 0:
            current_wpt = topo_stack.pop()

            result_lines.append(
                " ".join([airway_code,
                          f"{current_number:03d}",
                          id_point_map[current_wpt]["code"],
                          wpts[current_wpt][0],
                          wpts[current_wpt][1]]) + "\n"
            )

            current_number += 1

            if current_wpt in graph:
                for next_wpt in graph[current_wpt]:
                    if next_wpt in indegrees:
                        indegrees[next_wpt] -= 1
                        if indegrees[next_wpt] == 0:
                            topo_stack.append(next_wpt)

    with open("./merged/wpNavRTE.txt", "w") as fout:
        fout.writelines(result_lines)


icao_runways_map, id_point_map, icao_airport_map, waypoints, navaids, airways = read_pfpx_database()
apply_airway_coords()
merge_airports_apt()
merge_fix()
merge_aid()
recreate_rte()
