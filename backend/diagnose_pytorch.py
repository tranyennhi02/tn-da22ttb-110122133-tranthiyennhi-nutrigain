"""
Diagnostic script for PyTorch DLL issues
"""
import sys
import os

print("=" * 60)
print("PyTorch DLL Diagnostic")
print("=" * 60)
print()

print("1. Python version:")
print(f"   {sys.version}")
print()

print("2. Python executable:")
print(f"   {sys.executable}")
print()

print("3. Environment variables:")
for key in ['HF_HOME', 'TORCH_HOME', 'PATH']:
    value = os.environ.get(key, 'NOT SET')
    print(f"   {key}: {value[:100] if len(value) > 100 else value}")
print()

print("4. Attempting to import torch...")
try:
    import torch
    print(f"   ✓ Successfully imported torch {torch.__version__}")
    print()
    
    print("5. Attempting to import torch._C...")
    try:
        import torch._C
        print(f"   ✓ Successfully imported torch._C")
    except Exception as e:
        print(f"   ✗ Failed to import torch._C: {e}")
        print()
        print("6. Checking torch installation location:")
        print(f"   {torch.__file__}")
        
        # Check if torch DLLs exist
        torch_dir = os.path.dirname(torch.__file__)
        lib_dir = os.path.join(torch_dir, 'lib')
        print()
        print(f"7. Checking torch/lib directory: {lib_dir}")
        if os.path.exists(lib_dir):
            dlls = [f for f in os.listdir(lib_dir) if f.endswith('.dll')]
            print(f"   Found {len(dlls)} DLL files:")
            for dll in sorted(dlls)[:10]:  # Show first 10
                dll_path = os.path.join(lib_dir, dll)
                size = os.path.getsize(dll_path) / (1024 * 1024)  # MB
                print(f"   - {dll} ({size:.1f} MB)")
            if len(dlls) > 10:
                print(f"   ... and {len(dlls) - 10} more")
        else:
            print(f"   ✗ Directory does not exist!")
        
        raise
        
except Exception as e:
    print(f"   ✗ Failed to import torch: {e}")
    print()
    print("ERROR DETAILS:")
    import traceback
    traceback.print_exc()

print()
print("=" * 60)
