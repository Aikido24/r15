from pydantic import BaseModel, HttpUrl, model_validator


class AnalyzeRequest(BaseModel):
    document_url: HttpUrl | None = None
    image_url: HttpUrl | None = None

    @model_validator(mode="after")
    def validate_source_url(self) -> "AnalyzeRequest":
        if self.document_url is None and self.image_url is None:
            raise ValueError("Debes enviar document_url o image_url.")

        if self.document_url and self.image_url and self.document_url != self.image_url:
            raise ValueError("document_url e image_url deben coincidir si ambos se envian.")

        return self

    @property
    def source_url(self) -> str:
        return str(self.document_url or self.image_url)
