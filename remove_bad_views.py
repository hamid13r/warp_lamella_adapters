import os
import shutil
import glob
import pandas as pd
import xml.etree.ElementTree as ET
import io

# Step 1: Get list of XML files
xml_files = glob.glob("*.xml")

# Step 2: Make backup directory and copy XML files
backup_dir = "backup_xml"
os.makedirs(backup_dir, exist_ok=True)
#Step 3: go through XML files and set the UseTilt values based on taSolution.log
for xml_file in xml_files:
    #if the back up already exists, skip copying
    if os.path.exists(os.path.join(backup_dir, os.path.basename(xml_file))):
        print(f"Backup for {xml_file} already exists, skipping backup.")
    else:   
        shutil.copy(xml_file, backup_dir)
    
    # taSoliution.log has a header that needs to be skipped to read the data correctly
    log_path = os.path.join("tiltstack", os.path.splitext(os.path.basename(xml_file))[0], "taSolution.log")
    with open(log_path, "r") as f:
        lines = f.readlines()

    view_line_idx = None
    for idx, line in enumerate(lines):
        if 'view' in line:
            view_line_idx = idx
            break

    if view_line_idx is None:
        raise ValueError("No line with 'view' found in taSolution.log")

    data_str = ''.join(lines[view_line_idx:])
    df = pd.read_csv(io.StringIO(data_str), delim_whitespace=True)
    print(f"DataFrame for {xml_file}:\n{df}")
    # Get the list of included views from the DataFrame
    views_in_log = set(df['view'].unique())
    print(f"Views in log: {sorted(views_in_log)}")
    print(f"Number of views in log: {len(views_in_log)}")
    
    # For each XML file, check for missing views and update useTilt
    tree = ET.parse(xml_file)
    root = tree.getroot()
    
    # Find the UseTilt element and process its content
    use_tilt_elem = root.find('UseTilt')
    if use_tilt_elem is not None:
        # Get the current UseTilt values (split by newlines and filter empty strings)
        current_values = [val.strip() for val in use_tilt_elem.text.split('\n') if val.strip()]
        print(f"Original UseTilt values for {xml_file}: {len(current_values)} values")
        
        # Create a list to track which views to keep (True) or exclude (False)
        updated_values = []
        changes_made = 0
        
        for i, value in enumerate(current_values):
            # The view numbers in the log correspond to 1-based indexing
            # So XML index i corresponds to view number i+1 in the log
            view_number = i + 1
            if view_number in views_in_log:
                updated_values.append('True')
            else:
                updated_values.append('False')
                if value == 'True':  # Only count as a change if it was previously True
                    changes_made += 1
                print(f"  XML index {i} (view {view_number}) not found in log, setting to False")
        
        # Update the UseTilt element with the new values
        use_tilt_elem.text = '\n'.join(updated_values)
        print(f"Updated UseTilt values: {len(updated_values)} values, {changes_made} changes made")
        
    tree.write(xml_file)
