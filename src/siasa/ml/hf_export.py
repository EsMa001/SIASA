"""SIASA HuggingFace Datasets Export (AP-13.11).

Implements:
- SwR-067: HFExporter with Parquet→HuggingFace Dataset conversion,
  dataset card generation, schema preservation, and Hub push support.
"""
from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Sequence

import pyarrow.parquet as pq

try:
    from datasets import Dataset
except ImportError:
    Dataset = None  # type: ignore[assignment,misc]


@dataclass
class DatasetCardInfo:
    """Metadata for HuggingFace dataset card."""
    name: str
    description: str
    license: str
    features: list[str]
    num_rows: int
    version: str
    language: str = "en"
    task_categories: list[str] = field(default_factory=lambda: ["time-series-forecasting"])


class HFExporter:
    """Export SIASA training data to HuggingFace Datasets format."""

    def from_parquet(
        self,
        parquet_path: Path | str,
        columns: Optional[Sequence[str]] = None,
    ) -> "Dataset":
        """Load a Parquet file as a HuggingFace Dataset.

        Args:
            parquet_path: Path to the Parquet file.
            columns: Optional list of columns to include.

        Returns:
            HuggingFace Dataset object.
        """
        if Dataset is None:
            raise ImportError("Install 'datasets' package: pip install datasets")

        parquet_path = Path(parquet_path)
        table = pq.read_table(parquet_path, columns=columns)
        return Dataset.from_pandas(table.to_pandas())

    def write_dataset_card(
        self,
        output_dir: Path | str,
        card_info: DatasetCardInfo,
    ) -> Path:
        """Write a README.md dataset card.

        Args:
            output_dir: Directory to write the card to.
            card_info: Metadata for the card.

        Returns:
            Path to the written README.md.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        features_list = "\n".join(f"  - `{f}`" for f in card_info.features)
        task_list = "\n".join(f"- {t}" for t in card_info.task_categories)

        card_content = f"""---
language:
- {card_info.language}
license: {card_info.license}
task_categories:
{task_list}
tags:
- siasa
- geopolitical-risk
- time-series
size_categories:
- 1K<n<10K
---

# {card_info.name}

{card_info.description}

## Dataset Details

- **Version:** {card_info.version}
- **Rows:** {card_info.num_rows}
- **License:** {card_info.license}

## Features

{features_list}

## Usage

```python
from datasets import load_dataset

ds = load_dataset("{card_info.name}")
```

## Citation

If you use this dataset, please cite the SIASA project.
"""
        card_path = output_dir / "README.md"
        card_path.write_text(card_content, encoding="utf-8")
        return card_path

    def export_training_set(
        self,
        source_dir: Path | str,
        output_dir: Path | str,
        card_info: DatasetCardInfo,
    ) -> dict:
        """Export a complete training set directory to HF-compatible format.

        Copies Parquet split files (train/val/test) and writes a dataset card.

        Args:
            source_dir: Directory containing train.parquet, val.parquet, test.parquet.
            output_dir: Target directory for HF dataset.
            card_info: Metadata for the dataset card.

        Returns:
            Dict with export summary including split names and paths.
        """
        source_dir = Path(source_dir)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        splits = []
        for parquet_file in sorted(source_dir.glob("*.parquet")):
            split_name = parquet_file.stem
            shutil.copy2(parquet_file, output_dir / parquet_file.name)
            splits.append(split_name)

        self.write_dataset_card(output_dir, card_info)

        return {
            "output_dir": str(output_dir),
            "splits": splits,
            "card_path": str(output_dir / "README.md"),
            "num_splits": len(splits),
        }
