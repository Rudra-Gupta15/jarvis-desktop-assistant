import os
from automation import JarvisAutomation

auto = JarvisAutomation()

print("--- Testing Path Resolution ---")
# This should resolve to the real user path
p1 = "C:\\Users\\Username\\Pictures"
result1 = auto.open_folder(p1)
print(f"Result for {p1}: {result1}")

print("\n--- Testing Web Fallback ---")
# This should fallback to youtube.com
result2 = auto.open_app("youtube")
print(f"Result for youtube: {result2}")

# This should fallback to amazon.com
result3 = auto.open_app("amazon")
print(f"Result for amazon: {result3}")

# This should try to open a domain
result4 = auto.open_app("google.com")
print(f"Result for google.com: {result4}")
