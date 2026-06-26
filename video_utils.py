import os
import subprocess
import tempfile

def detections_to_segments(detected_seconds, sampling_interval=1.0, max_gap=1.5, min_duration=1.0, rejected_seconds=None):
    """Converts individual detected timestamps to continuous video segments.
    Args:
        detected_seconds: List of float, seconds where the person was detected.
        sampling_interval: float, interval at which frames were sampled.
        max_gap: float, maximum gap in seconds between segments to merge them.
        min_duration: float, minimum duration of a segment to be kept.
        rejected_seconds: List or set of float, seconds where non-selected persons were detected.
    Returns:
        List of tuples (start_sec, end_sec) representing the segments.
    """
    if not detected_seconds:
        return []
        
    if rejected_seconds is None:
        rejected_seconds = set()
    else:
        rejected_seconds = set(rejected_seconds)
    sorted_seconds = sorted(list(set(detected_seconds)))
    
    half_interval = sampling_interval / 2.0
    intervals = []
    for s in sorted_seconds:
        start = s - half_interval
        end = s + half_interval
        
        # If the block before s is rejected, clamp start to s to prevent bleeding
        if any(abs(r - (s - sampling_interval)) < 1e-4 for r in rejected_seconds):
            start = s
            
        intervals.append((max(0.0, start), end))
    
    merged = []
    current_start, current_end = intervals[0]
    
    for start, end in intervals[1:]:
        # Check if there is any explicitly rejected timestamp in the gap between current_end and start
        # Add a tiny tolerance (0.01) to avoid floating point precision issues.
        has_rejection_in_gap = any((current_end - 0.01) <= r <= (start + 0.01) for r in rejected_seconds)
        
        # If the gap between current_end and start is small and does not cross a rejected frame
        if start - current_end <= max_gap and not has_rejection_in_gap:
            current_end = end
        else:
            if current_end - current_start >= min_duration:
                merged.append((current_start, current_end))
            current_start, current_end = start, end
            
    # Append the last interval
    if current_end - current_start >= min_duration:
        merged.append((current_start, current_end))
        
    return merged

def trim_and_merge_video(input_video, segments, output_video, reencode=True, progress_callback=None):
    """Cuts the video into segments and merges them using FFmpeg.
    Args:
        input_video: Path to the source video.
        segments: List of tuples (start, end) in seconds.
        output_video: Path where the output video will be saved.
        reencode: Bool, if True, encodes video/audio to ensure frame-accurate cuts.
        progress_callback: Callback function to report progress.
    """
    if not segments:
        raise ValueError("No segments to extract.")
        
    temp_dir = tempfile.mkdtemp(prefix="video_trim_")
    segment_files = []
    
    try:
        total_segments = len(segments)
        for idx, (start, end) in enumerate(segments):
            if progress_callback:
                progress_callback(f"Cutting segment {idx+1}/{total_segments} ({start:.1f}s - {end:.1f}s)...", int(idx / total_segments * 90))
                
            temp_segment = os.path.join(temp_dir, f"segment_{idx:04d}.mp4")
            
            if reencode:
                # Frame-accurate output seeking with re-encoding
                duration = end - start
                cmd = [
                    "ffmpeg", "-y",
                    "-i", input_video,
                    "-ss", f"{start:.3f}",
                    "-t", f"{duration:.3f}",
                    "-c:v", "libx264",
                    "-preset", "superfast",
                    "-crf", "23",
                    "-c:a", "aac",
                    "-b:a", "128k",
                    temp_segment
                ]
            else:
                # Fast input seeking with direct stream copying
                cmd = [
                    "ffmpeg", "-y",
                    "-ss", f"{start:.3f}",
                    "-to", f"{end:.3f}",
                    "-i", input_video,
                    "-c", "copy",
                    temp_segment
                ]
                
            # Run the command silently
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            segment_files.append(temp_segment)
            
        if progress_callback:
            progress_callback("Merging segments...", 90)
            
        # Create text file for concat demuxer
        concat_file = os.path.join(temp_dir, "segments.txt")
        with open(concat_file, "w", encoding="utf-8") as f:
            for filepath in segment_files:
                # Escape backslashes for FFmpeg on Windows
                escaped_path = filepath.replace("\\", "/")
                f.write(f"file '{escaped_path}'\n")
                
        # Run FFmpeg concat demuxer
        concat_cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_file,
            "-c", "copy",
            output_video
        ]
        
        subprocess.run(concat_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        
        if progress_callback:
            progress_callback("Video processing complete!", 100)
            
    finally:
        # Clean up temporary segment files
        for f in segment_files:
            try:
                os.remove(f)
            except OSError:
                pass
        try:
            # Remove segments.txt
            os.remove(os.path.join(temp_dir, "segments.txt"))
        except OSError:
            pass
        try:
            os.rmdir(temp_dir)
        except OSError:
            pass

def trim_and_merge_multiple_videos(video_segments_dict, output_video, reencode=True, progress_callback=None):
    """Cuts segments from multiple input videos and merges them into a single file.
    Args:
        video_segments_dict: Dict mapping input_video path to a list of segments [(start, end), ...].
        output_video: Path where the single combined output video will be saved.
        reencode: Bool, if True, encodes video/audio to ensure frame-accurate cuts.
        progress_callback: Callback function to report progress.
    """
    if not video_segments_dict:
        raise ValueError("No video segments to extract.")
        
    temp_dir = tempfile.mkdtemp(prefix="video_trim_mult_")
    segment_files = []
    
    try:
        # Calculate total number of segments to track progress
        total_segments = sum(len(segs) for segs in video_segments_dict.values())
        if total_segments == 0:
            raise ValueError("No segments to extract.")
            
        current_idx = 0
        for video_path, segments in video_segments_dict.items():
            for idx, (start, end) in enumerate(segments):
                if progress_callback:
                    progress_callback(
                        f"Cutting {os.path.basename(video_path)} segment {idx+1}/{len(segments)} ({start:.1f}s - {end:.1f}s)...",
                        int(current_idx / total_segments * 90)
                    )
                    
                temp_segment = os.path.join(temp_dir, f"segment_{current_idx:04d}.mp4")
                
                if reencode:
                    # Frame-accurate output seeking with re-encoding
                    duration = end - start
                    cmd = [
                        "ffmpeg", "-y",
                        "-i", video_path,
                        "-ss", f"{start:.3f}",
                        "-t", f"{duration:.3f}",
                        "-c:v", "libx264",
                        "-preset", "superfast",
                        "-crf", "23",
                        "-c:a", "aac",
                        "-b:a", "128k",
                        temp_segment
                    ]
                else:
                    # Fast input seeking with direct stream copying
                    cmd = [
                        "ffmpeg", "-y",
                        "-ss", f"{start:.3f}",
                        "-to", f"{end:.3f}",
                        "-i", video_path,
                        "-c", "copy",
                        temp_segment
                    ]
                    
                # Run the command silently
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                segment_files.append(temp_segment)
                current_idx += 1
                
        if progress_callback:
            progress_callback("Merging all segments...", 90)
            
        # Create text file for concat demuxer
        concat_file = os.path.join(temp_dir, "segments.txt")
        with open(concat_file, "w", encoding="utf-8") as f:
            for filepath in segment_files:
                # Escape backslashes for FFmpeg on Windows
                escaped_path = filepath.replace("\\", "/")
                f.write(f"file '{escaped_path}'\n")
                
        # Run FFmpeg concat demuxer
        concat_cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_file,
            "-c", "copy",
            output_video
        ]
        
        subprocess.run(concat_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        
        if progress_callback:
            progress_callback("Video processing complete!", 100)
            
    finally:
        # Clean up temporary segment files
        for f in segment_files:
            try:
                os.remove(f)
            except OSError:
                pass
        try:
            os.remove(os.path.join(temp_dir, "segments.txt"))
        except OSError:
            pass
        try:
            os.rmdir(temp_dir)
        except OSError:
            pass

