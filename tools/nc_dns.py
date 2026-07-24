#!/usr/bin/env python3
"""
Namecheap DNS helper for dancykier.com.

⚠️  setHosts REPLACES the entire record set, and getHosts does NOT return the MX
records — Namecheap Private Email is driven by EmailType="OX", not by hosts. So
every write must re-send every existing record AND pass EmailType=OX, or Moshe's
email stops working. This script does both, and refuses to write if EmailType
comes back as anything other than OX.

  python3 nc_dns.py list
  python3 nc_dns.py add-cname 360 moshed.github.io.
"""

import subprocess, sys, urllib.parse, urllib.request
import xml.etree.ElementTree as ET

API = "https://api.namecheap.com/xml.response"
NS = {"nc": "http://api.namecheap.com/xml.response"}
SLD, TLD = "dancykier", "com"


def keychain(service):
    return subprocess.run(
        ["security", "find-generic-password", "-s", service, "-w"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()


def my_ip():
    with urllib.request.urlopen("https://api.ipify.org", timeout=15) as r:
        return r.read().decode().strip()


def call(command, extra=None):
    key, user, ip = keychain("namecheap_api_key"), keychain("namecheap_username"), my_ip()
    params = {
        "ApiUser": user, "ApiKey": key, "UserName": user, "ClientIp": ip,
        "Command": command, "SLD": SLD, "TLD": TLD,
    }
    params.update(extra or {})
    data = urllib.parse.urlencode(params).encode()
    with urllib.request.urlopen(API, data=data, timeout=60) as r:
        xml = r.read().decode()
    root = ET.fromstring(xml)
    if root.get("Status") != "OK":
        errs = [e.text for e in root.iter() if e.tag.endswith("Error")]
        sys.exit(f"Namecheap error ({command}) from IP {ip}: {errs}\n"
                 f"If this is 1011150, re-whitelist {ip} in Namecheap > Profile > Tools > API Access.")
    return root


def get_hosts():
    root = call("namecheap.domains.dns.getHosts")
    res = root.find(".//nc:DomainDNSGetHostsResult", NS)
    hosts = []
    for h in res.findall("nc:host", NS):
        hosts.append({
            "Name": h.get("Name"), "Type": h.get("Type"), "Address": h.get("Address"),
            "MXPref": h.get("MXPref") or "10", "TTL": h.get("TTL") or "1800",
        })
    return hosts, (res.get("EmailType") or "")


def set_hosts(hosts, email_type):
    if email_type != "OX":
        sys.exit(f"refusing to write: EmailType is {email_type!r}, expected 'OX' "
                 "(writing without it would break Private Email)")
    extra = {"EmailType": email_type}
    for i, h in enumerate(hosts, start=1):
        extra[f"HostName{i}"] = h["Name"]
        extra[f"RecordType{i}"] = h["Type"]
        extra[f"Address{i}"] = h["Address"]
        extra[f"MXPref{i}"] = h["MXPref"]
        extra[f"TTL{i}"] = h["TTL"]
    call("namecheap.domains.dns.setHosts", extra)
    print(f"wrote {len(hosts)} records, EmailType={email_type}")


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    cmd = sys.argv[1]
    hosts, et = get_hosts()

    if cmd == "list":
        print(f"EmailType={et}  ({len(hosts)} records)")
        for h in hosts:
            print(f"  {h['Type']:6} {h['Name']:24} -> {h['Address']}  ttl={h['TTL']}")
        return

    if cmd == "add-cname":
        name, target = sys.argv[2], sys.argv[3]
        if any(h["Name"] == name for h in hosts):
            sys.exit(f"host {name!r} already exists — edit it by hand, not with add-cname")
        hosts.append({"Name": name, "Type": "CNAME", "Address": target,
                      "MXPref": "10", "TTL": "1800"})
        set_hosts(hosts, et)
        return

    sys.exit(f"unknown command {cmd!r}")


if __name__ == "__main__":
    main()
