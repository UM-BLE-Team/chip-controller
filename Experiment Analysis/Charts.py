import pandas as pd
import matplotlib.pyplot as plt
import os

# Create output folder for charts
output_folder = "charts_output"
os.makedirs(output_folder, exist_ok=True)

# Load CSV files (adjust file names/paths as needed)
df1 = pd.read_csv("Experiment 1 - Distance 1 meter.csv")
df2 = pd.read_csv("Experiment 2 - Distance 4.5 meters.csv")
df3 = pd.read_csv("Experiment 3 - Distance 10 meters with wall.csv")

# Add a column for the distance condition (using file names as labels)
df1["Distance"] = "1 m"
df2["Distance"] = "4.5 m"
df3["Distance"] = "10 m with wall"

# Combine the data
df = pd.concat([df1, df2, df3], ignore_index=True)

# Ensure numeric columns are correct
numeric_cols = ["Round", "TotalPackets", "Duration(s)", "Throughput(p/s)", "Errors"]
for col in numeric_cols:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# Chart 1: Throughput per Round by Distance
plt.figure(figsize=(10, 6))
for distance, group in df.groupby("Distance"):
    plt.plot(group["Round"], group["Throughput(p/s)"], marker='o', label=f"Distance: {distance}")
plt.axhline(50, color="red", linestyle="--", label="Theoretical 50 p/s")
plt.title("Throughput per Round by Distance Condition")
plt.xlabel("Round")
plt.ylabel("Throughput (packets per second)")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.savefig(os.path.join(output_folder, "throughput_per_round.png"), dpi=300)
plt.close()

# Chart 2: Round Duration per Round by Distance
plt.figure(figsize=(10, 6))
for distance, group in df.groupby("Distance"):
    plt.plot(group["Round"], group["Duration(s)"], marker='o', label=f"Distance: {distance}")
plt.title("Round Duration by Distance Condition")
plt.xlabel("Round")
plt.ylabel("Duration (seconds)")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.savefig(os.path.join(output_folder, "round_duration.png"), dpi=300)
plt.close()

# Chart 3: Average Throughput by Distance
summary = df.groupby("Distance").agg({
    "TotalPackets": "sum",
    "Duration(s)": "sum",
    "Throughput(p/s)": "mean",
    "Round": "count"
}).reset_index()

plt.figure(figsize=(8, 6))
colors = ["#4CAF50", "#2196F3", "#FF9800"]
plt.bar(summary["Distance"], summary["Throughput(p/s)"], color=colors)
plt.title("Average Throughput by Distance Condition")
plt.xlabel("Distance")
plt.ylabel("Average Throughput (packets per second)")
plt.grid(axis="y")
plt.tight_layout()
plt.savefig(os.path.join(output_folder, "avg_throughput.png"), dpi=300)
plt.close()

# Chart 4: Round Duration vs. Total Packets by Distance
plt.figure(figsize=(10, 6))
for distance, group in df.groupby("Distance"):
    plt.scatter(group["TotalPackets"], group["Duration(s)"], s=100, label=f"Distance: {distance}")
plt.title("Round Duration vs. Total Packets by Distance")
plt.xlabel("Total Packets per Round")
plt.ylabel("Duration (seconds)")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.savefig(os.path.join(output_folder, "duration_vs_packets.png"), dpi=300)
plt.close()

# Chart 5: Total Errors by Distance (should be 0)
error_summary = df.groupby("Distance")["Errors"].sum().reset_index()
plt.figure(figsize=(8, 6))
plt.bar(error_summary["Distance"], error_summary["Errors"], color=colors)
plt.title("Total Error Count by Distance")
plt.xlabel("Distance")
plt.ylabel("Total Errors")
plt.tight_layout()
plt.savefig(os.path.join(output_folder, "total_errors.png"), dpi=300)
plt.close()

print("Charts saved in high resolution in the folder:", output_folder)
