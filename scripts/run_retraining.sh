#!/usr/bin/env sh
set -eu

python ml/training/build_curriculum_alignment_dataset.py
exec python ml/training/train_curriculum_ml_models.py
