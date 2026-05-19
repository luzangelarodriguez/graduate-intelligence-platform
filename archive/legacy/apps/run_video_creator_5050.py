# -*- coding: utf-8 -*-
import os
import runpy


os.environ["PORT"] = "5050"
runpy.run_path(os.path.join(os.path.dirname(__file__), "video_creator_app.py"), run_name="__main__")
