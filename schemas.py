from pydantic import BaseModel, Field
from typing import Optional


class ArvoreFeatures(BaseModel):
    """Input data: tree characteristics."""

    genre_bota: str = Field(
        ...,
        description="Botanical genus of the tree",
        examples=["Prunus", "Tilia", "Carpinus"],
    )
    espece: str = Field(
        ...,
        description="Tree species",
        examples=["serrulata", "henryana", "betulus"],
    )
    stadededeveloppement: str = Field(
        ...,
        description="Development stage",
        examples=["Young tree", "Adult tree", "Aging tree"],
    )
    hauteurarbre: str = Field(
        ...,
        description="Tree height",
        examples=["Less than 10 m", "10 m to 20 m", "More than 20 m"],
    )
    typenature: Optional[str] = Field(
        None,
        description="Growth form (may be null)",
        examples=["Free", "Semi-free", "Architectured"],
    )
    latitude: float = Field(
        ...,
        description="Latitude (Grenoble region)",
        ge=45.15,
        le=45.23,
        examples=[45.177],
    )
    longitude: float = Field(
        ...,
        description="Longitude (Grenoble region)",
        ge=5.69,
        le=5.80,
        examples=[5.727],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "genre_bota": "Prunus",
                    "espece": "serrulata",
                    "stadededeveloppement": "Young tree",
                    "hauteurarbre": "Less than 10 m",
                    "typenature": "Free",
                    "latitude": 45.167,
                    "longitude": 5.740,
                }
            ]
        }
    }


class PredictionResponse(BaseModel):
    """Prediction response."""

    annee_predite: float = Field(
        ...,
        description="Planting year estimated by the model",
        examples=[2008.3],
    )
    annee_arrondie: int = Field(
        ...,
        description="Estimated year rounded to an integer",
        examples=[2008],
    )


class HelpData(BaseModel):
    """User feedback: features + correction.

    annee_correcte is the real planting year provided by the user,
    used to compute the correction rate (Level 3 — Business KPI).
    label_correct is kept for compatibility with older schema versions
    (not used in KPI computation).
    """

    genre_bota: str
    espece: str
    stadededeveloppement: str
    hauteurarbre: str
    typenature: Optional[str]
    latitude: float
    longitude: float
    annee_correcte: Optional[int] = Field(
        None,
        description="Real planting year provided by the user (for correction rate computation)",
        examples=[2010],
    )
    label_correct: Optional[str] = Field(
        None,
        description="[Legacy] User categorical correction",
        examples=["churn", "stable"],
    )