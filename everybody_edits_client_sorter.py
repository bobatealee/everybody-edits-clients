import sys
import os
import zlib
import re
import hashlib
from datetime import datetime

def decompress_swf(data):
    signature = data[:3]
    if signature == b'FWS':
        return data
    elif signature == b'CWS':
        decompressed = zlib.decompress(data[8:])
        return b'FWS' + data[3:8] + decompressed
    elif signature == b'ZWS':
        raise ValueError("ZWS (LZMA) compression not supported")
    else:
        raise ValueError("Unknown SWF format")

def extract_date(swf_data):
    match = re.search(rb'<rdf:RDF.*?</rdf:RDF>', swf_data, re.DOTALL)
    if not match:
        return None
    xml = match.group(0).decode(errors='ignore')
    match = re.search(r'<dc:date>(.*?)</dc:date>', xml)
    if match:
        return match.group(1)
    return None

def format_date(date_str):
    try:
        dt = datetime.strptime(date_str, "%b %d, %Y")
        return dt.strftime("%Y_%m_%d")
    except:
        return "unknown_date"

def extract_version(filename):
    match = re.search(r'v(\d+)', filename, re.IGNORECASE)
    if match:
        return f"v{match.group(1)}"
    return "unknown"

def main():
    if len(sys.argv) < 2:
        print("Drag SWF file(s) onto this script.")
        return

    # Only consider dragged client files
    swf_files = [path.strip('"') for path in sys.argv[1:] if path.lower().endswith('.swf') and os.path.isfile(path)]
    if not swf_files:
        print("No SWF files found.")
        return

    print(f"Found {len(swf_files)} SWF file(s). Processing...")

    # Collect all client info
    file_infos = []
    for path in swf_files:
        try:
            with open(path, 'rb') as f:
                raw = f.read()
            swf = decompress_swf(raw)
            raw_date = extract_date(swf)
            formatted_date = format_date(raw_date) if raw_date else "unknown_date"
            version = extract_version(os.path.basename(path))
            h = hashlib.sha256(raw).hexdigest()
            file_infos.append({
                'original_path': path,
                'hash': h,
                'date': formatted_date,
                'version': version,
                'base_name': f"{formatted_date}_{version}",
                'directory': os.path.dirname(path)
            })
        except Exception as e:
            print(f"Error processing {path}: {e}")

    # Group by hash to detect byte-for-byte duplicates
    hash_groups = {}
    for info in file_infos:
        hash_groups.setdefault(info['hash'], []).append(info)

    # Assign conflicted status to all byte-for-byte duplicates
    for group in hash_groups.values():
        if len(group) > 1:
            for info in group:
                info['final_base'] = f"{info['base_name']}_conflicted"
        else:
            group[0]['final_base'] = group[0]['base_name']

    # Resolve filename conflicts within the same batch
    generated_names = {}
    for info in file_infos:
        directory = info['directory']
        generated_names.setdefault(directory, set())
        ext = ".swf"
        final_name = info['final_base'] + ext
        counter = 2
        while final_name in generated_names[directory]:
            final_name = f"{info['final_base']}_{counter}{ext}"
            counter += 1
        info['final_name'] = final_name
        generated_names[directory].add(final_name)

    # Rename all files
    for info in file_infos:
        try:
            os.rename(info['original_path'], os.path.join(info['directory'], info['final_name']))
            print(f"Renamed: {os.path.basename(info['original_path'])} -> {info['final_name']}")
        except Exception as e:
            print(f"Error renaming {info['original_path']}: {e}")

    print("\nProcessing complete.")

if __name__ == "__main__":
    main()