"""Data Analysis Skill - CSV/Excel analiz."""
from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import structlog

from skills.base_skill import BaseSkill, skill_registry

logger = structlog.get_logger(__name__)


class DataAnalysisSkill(BaseSkill):
    """CSV/Excel dosyalarini analiz eder."""

    name = "data_analysis"
    description = "CSV/Excel veri analizi (istatistik + ozet)"

    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

    async def read_csv(self, content: str | bytes) -> Any:
        """CSV okur."""
        try:
            import pandas as pd
        except ImportError:
            raise ImportError("pandas gerekli: uv pip install pandas")

        if isinstance(content, bytes):
            content = content.decode("utf-8")

        return pd.read_csv(io.StringIO(content))

    async def read_excel(self, content: bytes) -> Any:
        """Excel okur."""
        try:
            import pandas as pd
        except ImportError:
            raise ImportError("pandas + openpyxl gerekli")

        return pd.read_excel(io.BytesIO(content))

    def analyze_dataframe(self, df: Any) -> dict[str, Any]:
        """DataFrame'i analiz eder."""
        result: dict[str, Any] = {
            "rows": len(df),
            "columns": len(df.columns),
            "column_names": list(df.columns),
            "dtypes": {col: str(df[col].dtype) for col in df.columns},
            "missing_values": {col: int(df[col].isna().sum()) for col in df.columns},
            "memory_usage_kb": round(df.memory_usage(deep=True).sum() / 1024, 2),
        }

        # Sayisal kolonlar icin istatistikler
        numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
        if numeric_cols:
            stats = {}
            for col in numeric_cols:
                stats[col] = {
                    "min": float(df[col].min()),
                    "max": float(df[col].max()),
                    "mean": round(float(df[col].mean()), 2),
                    "median": float(df[col].median()),
                    "std": round(float(df[col].std()), 2),
                    "sum": float(df[col].sum()),
                }
            result["numeric_stats"] = stats

        # Kategorik kolonlar icin top degerler
        cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
        if cat_cols:
            cat_info = {}
            for col in cat_cols[:5]:  # max 5 kolon
                value_counts = df[col].value_counts().head(5).to_dict()
                cat_info[col] = {str(k): int(v) for k, v in value_counts.items()}
            result["categorical_top"] = cat_info

        # Ilk 5 satir (preview)
        result["head"] = df.head(5).to_dict(orient="records")

        return result

    async def execute(
        self,
        content: str | bytes = "",
        file_format: str = "csv",
        **kwargs,
    ) -> dict[str, Any]:
        """Veriyi analiz eder."""
        if not content:
            return {"error": "Icerik bos"}

        # Boyut kontrolu
        size = len(content) if isinstance(content, (str, bytes)) else 0
        if size > self.MAX_FILE_SIZE:
            return {"error": f"Dosya cok buyuk (max {self.MAX_FILE_SIZE // 1024 // 1024} MB)"}

        try:
            if file_format == "csv":
                df = await self.read_csv(content)
            elif file_format == "excel":
                if not isinstance(content, bytes):
                    return {"error": "Excel icin bytes gerekli"}
                df = await self.read_excel(content)
            else:
                return {"error": f"Desteklenmeyen format: {file_format}"}

            logger.info("data_analysis.read", rows=len(df), cols=len(df.columns))
            analysis = self.analyze_dataframe(df)

            return {
                "analysis": analysis,
                "summary": self._format_summary(analysis),
            }

        except ImportError as e:
            return {"error": f"Eksik paket: {str(e)}"}
        except Exception as e:
            logger.exception("data_analysis.error", error=str(e))
            return {"error": f"Analiz hatasi: {str(e)}"}

    def _format_summary(self, analysis: dict[str, Any]) -> str:
        """Analizi okunabilir metin haline getirir."""
        lines = [
            f"Satir: {analysis['rows']}, Kolon: {analysis['columns']}",
            f"Kolonlar: {', '.join(analysis['column_names'])}",
        ]

        if analysis.get("missing_values"):
            missing = {k: v for k, v in analysis["missing_values"].items() if v > 0}
            if missing:
                lines.append(f"Eksik degerler: {missing}")

        if analysis.get("numeric_stats"):
            lines.append("\nSayisal Istatistikler:")
            for col, stats in list(analysis["numeric_stats"].items())[:5]:
                lines.append(
                    f"  {col}: min={stats['min']}, max={stats['max']}, "
                    f"ort={stats['mean']}, medyan={stats['median']}"
                )

        return "\n".join(lines)


# Kayit
skill_registry.register(DataAnalysisSkill())
