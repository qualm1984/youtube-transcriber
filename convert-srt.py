def convert_transcript_to_srt(file_path, output_srt_path):
    # Open and read the entire file
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()
    
    srt_entries = []
    for line in lines:
        # Assuming each line is formatted as "[start_time -> end_time] text"
        if '->' in line:
            parts = line.split(' ')
            start_time = parts[0].replace('[', '').replace('s', '')
            end_time = parts[2].replace('s', '').replace(']', '')
            text = ' '.join(parts[3:]).strip()

            # Convert times into SRT format
            start_time_srt = f"{int(float(start_time) // 3600):02d}:{int((float(start_time) % 3600) // 60):02d}:{int(float(start_time) % 60):02d},{int((float(start_time) % 1) * 1000):03d}"
            end_time_srt = f"{int(float(end_time) // 3600):02d}:{int((float(end_time) % 3600) // 60):02d}:{int(float(end_time) % 60):02d},{int((float(end_time) % 1) * 1000):03d}"
            
            srt_entries.append(f"{start_time_srt} --> {end_time_srt}\n{text}\n")

    # Write to SRT file
    with open(output_srt_path, 'w', encoding='utf-8') as srt_file:
        for i, entry in enumerate(srt_entries, start=1):
            srt_file.write(f"{i}\n{entry}\n")

# Example usage
file_path = 'e73.txt'  # Change this to your transcript file path
output_srt_path = 'output_subtitle.srt'
convert_transcript_to_srt(file_path, output_srt_path)
