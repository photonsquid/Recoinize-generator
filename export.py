from alive_progress import alive_bar
from datasets import load_dataset
import shutil
import jsonlines
import os
import re
import argparse

DEFAULT_INPUT_DIR = "out/rendered"
DEFAULT_OUTPUT_DIR = "out/dataset"

def split_dataset(src, out, train_ratio, valid_ratio, test_ratio, regex=".+\.png$") -> None:
    # Make sure bothe the source and output directories exist
    if not os.path.exists(src):
      raise Exception("Source directory does not exist")
    if not os.path.exists(out):
      os.makedirs(out)
    
    # Make sure the ratios add up to 1
    if train_ratio + valid_ratio + test_ratio != 1:
      raise Exception("Ratios must add up to 1")

    # Get the list of files in the source directory
    files = os.listdir(src)
    files = [f for f in files if re.match(regex, f)]

    metadata = []
    # Classify the images
    for file in files:
      # Get the country, value, category, and variant from the filename
      file_data = os.path.splitext(file)[0].split("_")
      country = file_data[0]
      value = file_data[1]
      if len(file_data) == 4:
        edition = file_data[2]
        variant = file_data[3]
      else:
        edition = "standard"
        variant = file_data[2]
      
      metadata.append({
        "file_name": file,
        "labels": {
          "value": value,
          "country": country,
          "edition": edition,
          "variant": variant
        }
      })

    # Create the output directories
    os.makedirs(os.path.join(out, "train"))
    os.makedirs(os.path.join(out, "valid"))
    os.makedirs(os.path.join(out, "test"))

    # Determine number of variants for each country and value
    variants = max([int(data["labels"]["variant"]) for data in metadata]) + 1

    # Split the dataset into train, valid, and test
    with alive_bar(len(metadata)) as bar:
      for i, data in enumerate(metadata):
        # Get the file name and the destination directory
        file = data["file_name"]
        variant =int(data["labels"]["variant"])
        if variant < train_ratio * variants:
          dest = "train"
        elif variant < (train_ratio + valid_ratio) * variants:
          dest = "valid"
        else:
          dest = "test"

        # Copy the file to the destination directory
        shutil.copyfile(os.path.join(src, file), os.path.join(out, dest, file))
      
        # Write the metadata to a JSON Lines file
        with jsonlines.open(os.path.join(out, dest, "metadata.jsonl"), "a") as writer:
          writer.write(data)

        bar.text = f"Copying {file}"
        bar()
    
if __name__ == "__main__":
  # Parse the command line arguments
  parser = argparse.ArgumentParser()
  parser.add_argument("--input_dir", type=str, default=DEFAULT_INPUT_DIR, help="The directory containing the images to split")
  parser.add_argument("--output_dir", type=str, default=DEFAULT_OUTPUT_DIR, help="The directory to output the dataset to")
  args = parser.parse_args()

  input_dir = args.input_dir
  output_dir = args.output_dir

  # If the output directory already exists and is not empty, skip this step
  if not os.path.exists(output_dir) or len(os.listdir(output_dir)) == 0:
    split_dataset(input_dir, output_dir, 0.7, 0.15, 0.15, regex="^(?!.*_mask).+\.png$")
  else:
    print("Output directory already exists, skipping")
  
  # Upload the dataset to Hugging Face
  print("Compiling dataset")
  dataset = load_dataset(output_dir)

  print("Uploading dataset to Hugging Face")
  dataset.push_to_hub("photonsquid/coins-euro")