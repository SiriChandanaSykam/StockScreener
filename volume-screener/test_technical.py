import Technical
import inspect

print("Technical path:", Technical.__path__)

# Try to import likely submodules
for mod in ["NSE_Equity", "NSE_Index", "NSE_Futures", "BSE_Equity"]:
    try:
        m = __import__(f"Technical.{mod}", fromlist=["*"])
        print(f"\nModule Technical.{mod} loaded")
        print("Functions:", [n for n, o in inspect.getmembers(m) if inspect.isfunction(o)])
    except ImportError as e:
        print(f"\nCannot import Technical.{mod}:", e)
