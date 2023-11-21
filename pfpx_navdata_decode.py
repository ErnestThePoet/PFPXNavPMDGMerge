with open("./PFPX/navdata.nav", "rb") as fin:
    raw_pfpx_navdata = bytearray(fin.read()[65:])
    for i in range(len(raw_pfpx_navdata)):
        if raw_pfpx_navdata[i] not in (ord("\r"), ord("\n")):
            raw_pfpx_navdata[i] ^= 0x85

    with open("./PFPX/decoded.nav", "wb") as fout:
        fout.write(raw_pfpx_navdata)
