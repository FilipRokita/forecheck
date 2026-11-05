"""Configuration from the environment (and a local ``.env``). The only place that reads it."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from forecheck import __version__
from forecheck.domain.rules import Rules
from forecheck.domain.types import Variable


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    # Pooled connection string for the app. Required for anything that touches the database.
    database_url: str = ""
    # Protects the scheduled route. Empty disables the route.
    cron_secret: str = ""
    # Sent in the User-Agent to the data providers, so they can tell this deployment apart and
    # reach whoever runs it. Both are optional: nothing identifying is sent that is not set here.
    app_url: str = ""
    contact_email: str = ""

    # How forecasts are judged. The defaults are the method's; override to experiment.
    precipitation_threshold_mm: float = Field(default=0.1, gt=0)
    min_samples: int = Field(default=10, ge=1)
    trust_temperature_mae_c: float = Field(default=2.0, gt=0)
    trust_wind_mae_ms: float = Field(default=1.5, gt=0)
    trust_pressure_mae_hpa: float = Field(default=2.0, gt=0)
    trust_precipitation_accuracy: float = Field(default=0.8, gt=0, le=1)

    @property
    def user_agent(self) -> str:
        details = [f"+{self.app_url}"] if self.app_url else []
        if self.contact_email:
            details.append(self.contact_email)
        return f"forecheck/{__version__}" + (f" ({'; '.join(details)})" if details else "")

    def rules(self) -> Rules:
        return Rules(
            precipitation_threshold_mm=self.precipitation_threshold_mm,
            min_samples=self.min_samples,
            trust_thresholds={
                Variable.TEMPERATURE: self.trust_temperature_mae_c,
                Variable.WIND: self.trust_wind_mae_ms,
                Variable.PRESSURE: self.trust_pressure_mae_hpa,
                Variable.PRECIPITATION: self.trust_precipitation_accuracy,
            },
        )
