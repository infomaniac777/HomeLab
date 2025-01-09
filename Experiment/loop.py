import time

def infinite_counter():
    counter = 0
    while True:
        counter += 1
        if counter % 1000000 == 0:
            print(f"Count: {counter}")
            counter = 0  # Reset to prevent growing memory usage
            time.sleep(2)

if __name__ == "__main__":
    print("Starting infinite loop... Check CPU usage with 'top' or Task Manager")
    print("Press Ctrl+C to stop")
    infinite_counter()