from pydantic import BaseModel, Field
from typing import Optional


class ArvoreFeatures(BaseModel):
    """Dados de entrada: características da árvore."""

    genre_bota: str = Field(
        ...,
        description="Gênero botânico da árvore",
        examples=["Prunus", "Tilia", "Carpinus"],
    )
    espece: str = Field(
        ...,
        description="Espécie da árvore",
        examples=["serrulata", "henryana", "betulus"],
    )
    stadededeveloppement: str = Field(
        ...,
        description="Estágio de desenvolvimento",
        examples=["Arbre jeune", "Arbre adulte", "Arbre vieillissant"],
    )
    hauteurarbre: str = Field(
        ...,
        description="Altura da árvore",
        examples=["Moins de 10 m", "de 10 m à 20 m", "Plus de 20 m"],
    )
    typenature: Optional[str] = Field(
        None,
        description="Tipo de porte (pode ser nulo)",
        examples=["Libre", "Semi-libre", "Architecturé"],
    )
    latitude: float = Field(
        ...,
        description="Latitude (região de Grenoble)",
        ge=45.15,
        le=45.23,
        examples=[45.177],
    )
    longitude: float = Field(
        ...,
        description="Longitude (região de Grenoble)",
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
                    "stadededeveloppement": "Arbre jeune",
                    "hauteurarbre": "Moins de 10 m",
                    "typenature": "Libre",
                    "latitude": 45.167,
                    "longitude": 5.740,
                }
            ]
        }
    }


class PredictionResponse(BaseModel):
    """Resposta da predição."""

    annee_predite: float = Field(
        ...,
        description="Ano de plantio estimado pelo modelo",
        examples=[2008.3],
    )
    annee_arrondie: int = Field(
        ...,
        description="Ano arredondado para inteiro",
        examples=[2008],
    )

class HelpData(BaseModel):
    """Feedback do usuário: features + label correto."""

    genre_bota: str
    espece: str
    stadededeveloppement: str
    hauteurarbre: str
    typenature: Optional[str]
    latitude: float
    longitude: float
    label_correct: str = Field(
        ...,
        description="Correção do usuário: churn ou stable",
        examples=["churn", "stable"],
    )
