import sys
import os
import flet as ft

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.client.main import main

if __name__ == "__main__":
    ft.app(target=main)