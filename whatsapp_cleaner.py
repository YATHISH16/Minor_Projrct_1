import re #importing regular expression to scan and match patterns
import pandas as pd #to create cleaned dataframe
from datetime import datetime #to convert str timestamps into datetime objects

def clean_whatsapp_log(input_file_path):

    # to match 24hr logs("DD/MM/YY,HH:MM - Name:Msg")
    pattern_24h = re.compile(r'^(\d{2}/\d{2}/\d{2,4}),\s(\d{2}:\d{2})\s-\s([^:]+):\s(.*)$')
    # to match 12hr logs("DD/MM/YY,HH:MM - Name:Msg")
    pattern_12h = re.compile(r'^(\d{2}/\d{2}/\d{2,4}),\s(\d{1,2}:\d{2}\s*[A-Z]{2})\s-\s([^:]+):\s(.*)$')

    cleaned_records = [] #to store cleaned records
    #opens file and uses UTF-8 encoding to support emojis
    with open(input_file_path, 'r', encoding='utf-8') as file:
        for line in file:
            line_str = line.strip()#to remove white spaces i.e( hello )
            if not line_str:
                continue #tto skip empty lines  

            match = pattern_24h.match(line_str)#matching with 24hr pattern
            time_type = "24h"

            if not match:
                match = pattern_12h.match(line_str)#matching with 12hr pattern
                time_type = "12h"
                
            if match:
                date_str, time_str, sender, message = match.groups()#unpacks into 4 variables
                
                # To exclude system notifications
                system_triggers = ["created group", "added you", "changed the group", "left the group", "was added", "messages are end-to-end encrypted"]
                if any(trigger in message.lower() for trigger in system_triggers):
                    continue #to skip notifications
                
                cleaned_records.append({
                    'raw_date': date_str,
                    'raw_time': time_str,
                    'time_type': time_type,
                    'sender': sender.strip(),
                    'message': message.strip()
                }) #adds cleaned record as dict
            else: #no match (continuous message)
                #appends multi-line content back to the last message row
                if cleaned_records:
                    cleaned_records[-1]['message'] += " " + line_str

    if not cleaned_records:
        raise ValueError("Could not extract structural log profiles. Check raw file layout style.")

    df = pd.DataFrame(cleaned_records) #converting into pandas df
    
    #to standardize Datetime parameters
    standardized_timestamps = [] #to store standardized timestamps
    for _, row in df.iterrows(): #iterate through every rows
        try:
            # to determine the year format based on length(2026 vs 26)
            year_format = '%d/%m/%Y' if len(row['raw_date'].split('/')[-1]) == 4 else '%d/%m/%y'
            #uses 12hr if 12 else 24hr.
            time_format = '%I:%M %p' if row['time_type'] == "12h" else '%H:%M'
            
            #to clean micro-spaces placed by mobile os(e.g:iOS)
            clean_time_str = row['raw_time'].replace(' ', ' ').replace('  ', ' ').strip()
            
            #Combines the date and time strings into datetime obj.
            dt = datetime.strptime(f"{row['raw_date']} {clean_time_str}", f"{year_format} {time_format}")
            standardized_timestamps.append(dt)#appends new timestamp

        except Exception:
            standardized_timestamps.append(pd.NaT)#inserts blank value for unparseable timestamps
            
    df['timestamp'] = standardized_timestamps #adds into dataframe as new column

    #delete rows with broken timestamps and sort by timestamp
    df = df.dropna(subset=['timestamp']).sort_values('timestamp').reset_index(drop=True)
    
    # Dimensions Feature engineering 
    df['date'] = df['timestamp'].dt.date #extacts date
    df['hour'] = df['timestamp'].dt.hour #extracts hour
    
    return df
