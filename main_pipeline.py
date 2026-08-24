import pytest
import os
import sys

def main():
    print("Initializing Project Kavach Main Pipeline...")
    print("Running end-to-end integration tests using pytest...")
    
    # Run pytest programmatically
    args = ["-v", "test_api.py"]
    
    # Capture exit code
    exit_code = pytest.main(args)
    
    print(f"\nPipeline finished with exit code: {exit_code}")
    
    if exit_code == 0:
        print("Success! All systems (Similarity Guard, Crypto Core, Watermark Engine, and API) are fully operational.")
        sys.exit(0)
    else:
        print("Pipeline Failed. Review logs for details.")
        sys.exit(1)

if __name__ == "__main__":
    main()
