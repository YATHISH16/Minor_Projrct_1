import re
import numpy as np
import pandas as pd
from whatsapp_cleaner import clean_whatsapp_log

def run_groupdna_analysis(file_path):
    df = clean_whatsapp_log(file_path)
    total_messages = len(df)
    unique_members = df['sender'].nunique()
    
    total_days = (df['timestamp'].max() - df['timestamp'].min()).days + 1
    total_days = max(total_days, 1)
    start_date_str = df['timestamp'].min().strftime('%d %B %Y')
    end_date_str = df['timestamp'].max().strftime('%d %B %Y')
    
    busiest_day_date = df['date'].value_counts().idxmax()
    busiest_day_count = df['date'].value_counts().max()
    busiest_day_str = busiest_day_date.strftime('%d %B %Y')
    b_hour = df['hour'].value_counts().idxmax()
    busiest_hour_str = f"{b_hour:02d}:00 - {b_hour+1:02d}:00"
    
    def generate_ascii_bar(val, max_v, width=20):
        if max_v == 0: return "."
        chars = round((val / max_v) * width)
        return "█" * chars + " " * (width - chars) if chars > 0 else "."
        
    sender_counts = df['sender'].value_counts()
    max_msgs = sender_counts.max()
    
    clean_text = df['message'].str.lower().str.replace(r'[^\w\s]', '', regex=True)
    all_words = " ".join(clean_text.fillna("")).split()
    stop_words = {'to', 'is', 'the', 'and', 'a', 'in', 'i', 'you', 'was', 'this', 'that', 'with', 'for', 'of', 'on', 'my', 'me', 'it', 'at', 'omitted', 'media'}
    filtered_words = [w for w in all_words if w not in stop_words and len(w) > 1]
    word_freq = pd.Series(filtered_words).value_counts()
    
    df['streak_id'] = (df['sender'] != df['sender'].shift()).cumsum()
    burst_streaks = df.groupby(['sender', 'streak_id']).size().groupby('sender').mean()
    
    caring_keywords = ['eat', 'food', 'safe', 'study', 'water', 'worry', 'notes', 'home', 'care', 'dinner', 'breakfast']
    caring_score = df['message'].str.lower().apply(lambda x: sum(1 for w in caring_keywords if w in str(x))).groupby(df['sender']).sum()
    
    night_msgs = df[(df['hour'] >= 23) | (df['hour'] <= 4)]
    night_owl_pct = (night_msgs['sender'].value_counts() / sender_counts).fillna(0) * 100
    
    word_counts = df['message'].apply(lambda x: len(str(x).split())).groupby(df['sender']).mean()
    all_caps_pct = df['message'].apply(lambda x: 1 if str(x).isupper() and len(re.sub(r'[^A-Z]', '', str(x))) > 3 else 0).groupby(df['sender']).mean() * 100
    
    unique_days_active = df.groupby('sender')['date'].nunique()
    silent_days_count = total_days - unique_days_active

    # --- DYNAMIC LOOKUPS FOR PERSONALITY ARCHETYPES ---
    top_spammer = burst_streaks.idxmax() if not burst_streaks.empty else "N/A"
    top_caring = caring_score.idxmax() if not caring_score.empty else "N/A"
    top_night_owl = night_owl_pct.idxmax() if not night_owl_pct.empty else "N/A"
    top_storyteller = word_counts.idxmax() if not word_counts.empty else "N/A"
    top_drama = all_caps_pct.idxmax() if not all_caps_pct.empty else "N/A"
    top_ghost = silent_days_count.idxmax() if not silent_days_count.empty else "N/A"
    
    print("=" * 60)
    print("GROUPDNA DYNAMIC DATA REPORT")
    print(f"{total_days} days • {total_messages:,} messages • {unique_members} members")
    print("=" * 60)
    print(f"Period       : {start_date_str} to {end_date_str}")
    print(f"Busiest day  : {busiest_day_str} ({busiest_day_count} messages)")
    print(f"Busiest hour : {busiest_hour_str}")
    
    print("\nMESSAGES PER PERSON")
    for name, count in sender_counts.items():
        pct = (count / total_messages) * 100
        bar = generate_ascii_bar(count, max_msgs)
        print(f"{name:<12} {bar} {count:>3} ({pct:>4.1f}%)")
        
    print("\nACTIVITY HEATMAP (hour of day, columns 00 to 23)")
    print("             00  03  06  09  12  15  18  21")
    target_hours = [0, 3, 6, 9, 12, 15, 18, 21]
    for name in sender_counts.index:
        markers = []
        for h in target_hours:
            h_count = len(df[(df['sender'] == name) & (df['hour'] == h)])
            if h_count > 15: markers.append("█")
            elif h_count > 5: markers.append("▒")
            elif h_count > 0: markers.append("░")
            else: markers.append(".")
        suffix = " <- NIGHT OWL" if name == top_night_owl else ""
        print(f"{name:<12} " + "   ".join(markers) + suffix)
        
    print("\nTHIS GROUP'S FAVOURITE WORDS")
    max_w_count = word_freq.iloc[0] if not word_freq.empty else 1
    for word, count in word_freq.head(5).items():
        bar = generate_ascii_bar(count, max_w_count)
        print(f"{word:<12} {bar} {count}")
        
    print("\nLONGEST SILENT STREAKS (Total Days Inactive)")
    for name, s_days in silent_days_count.sort_values(ascending=False).items():
        print(f"{name:<12} : {s_days} days")
        
    print("\nPERSONALITY ARCHETYPES")
    if top_spammer != "N/A":
        print(f"{top_spammer:<12} → THE SPAMMER (avg {burst_streaks.get(top_spammer, 0):.1f} msgs in a row)")
    if top_caring != "N/A":
        print(f"{top_caring:<12} → THE GROUP MOM (caring keyword score: {caring_score.get(top_caring, 0)})")
    if top_night_owl != "N/A":
        print(f"{top_night_owl:<12} → THE NIGHT OWL ({night_owl_pct.get(top_night_owl, 0):.1f}% msgs between 23h-04h)")
    if top_storyteller != "N/A":
        print(f"{top_storyteller:<12} → THE STORYTELLER (avg {word_counts.get(top_storyteller, 0):.1f} words per msg)")
    if top_drama != "N/A":
        print(f"{top_drama:<12} → THE DRAMA QUEEN ({all_caps_pct.get(top_drama, 0):.1f}% ALL-CAPS messages)")
    if top_ghost != "N/A":
        print(f"{top_ghost:<12} → THE GHOST (silent on {silent_days_count.get(top_ghost, 0)} of {total_days} days)")
        
    print("=" * 60)
    print("Generated by GroupDNA • Built with Python + NumPy")
    print("=" * 60)

if __name__ == "__main__":
    run_groupdna_analysis("hostel_bois.txt")
