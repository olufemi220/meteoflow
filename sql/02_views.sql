CREATE OR REPLACE VIEW weather_daily AS
SELECT city,
       date(measured_at)          AS jour,
       round(avg(temperature), 1) AS temp_moy,
       max(temperature)           AS temp_max
FROM weather_measurements
GROUP BY city, date(measured_at);
