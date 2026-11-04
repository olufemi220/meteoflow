CREATE TABLE IF NOT EXISTS weather_measurements (
  city         VARCHAR(100) NOT NULL,
  measured_at  TIMESTAMPTZ  NOT NULL,
  temperature  NUMERIC(5,2),
  humidity     NUMERIC(5,2),
  wind_speed   NUMERIC(6,2),
  ingested_at  TIMESTAMPTZ  DEFAULT now(),
  PRIMARY KEY (city, measured_at)          -- l'UPSERT évite les doublons
);

CREATE INDEX IF NOT EXISTS idx_weather_measured_at
  ON weather_measurements (measured_at);
