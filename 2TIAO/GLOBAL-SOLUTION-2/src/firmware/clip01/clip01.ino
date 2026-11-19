/*
 * WARNED. CLIP-01 · TAG 3D — firmware de prova de conceito (ESP32)
 * Simulável no Wokwi (diagram.json nesta pasta).
 *
 * Sensores no Wokwi:
 *   - HX711 + célula de carga  -> força na guia (kgf)
 *   - MPU6050 (IMU)            -> inclinação do clip, para projetar Z na vertical
 *   - Potenciômetro            -> substitui o barômetro BMP280 (o Wokwi não tem BMP280):
 *                                 representa a altitude do sensor de 752.0 a 753.5 m
 *   - Botão                    -> BTN MODO LED
 *   - LED                      -> sinal visual no escuro
 *
 * Saída: uma linha JSON por segundo na Serial (o app do tutor leria por BLE).
 * Exemplo: {"dog":8695,"kgf":3.4,"n":33,"faixa":"TRACAO","z_cm":61.0,"pk":8.6,"led":0,"uA":14}
 *
 * Valores de consumo (14 µA / 184 d) são META DE PROJETO com deep sleep; esta POC
 * roda em loop contínuo para facilitar a demonstração.
 */
#include <Wire.h>
#include <HX711.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <math.h>

#define PIN_HX_DT   16
#define PIN_HX_SCK  4
#define PIN_POT     34
#define PIN_BTN     15
#define PIN_LED     2

const int   DOG_ID      = 8695;
const float KGF_TO_N    = 9.80665f;
const float FROUXA      = 2.5f;
const float TRANCO      = 8.0f;
const float HX_SCALE    = 420.0f;   // calibração da célula (unidades HX711 por kgf)
const float GOOGLE_ELEV = 752.10f;  // cota do terreno da célula H3 (cache vindo do app)
const float EMA_ALPHA   = 0.2f;     // filtro do barômetro

HX711 balanca;
Adafruit_MPU6050 imu;
bool imuOk = false, led = false, btnAnterior = HIGH;
float elevFiltrada = NAN, pico = 0;

const char* faixa(float kgf) {
  if (kgf < FROUXA) return "FROUXA";
  if (kgf <= TRANCO) return "TRACAO";
  return "TRANCO";
}

float lerElevacaoSensor() {
  // Potenciômetro 0..4095 -> 752.0..753.5 m (substitui o BMP280 no simulador)
  float bruto = 752.0f + analogRead(PIN_POT) * (1.5f / 4095.0f);
  elevFiltrada = isnan(elevFiltrada) ? bruto : EMA_ALPHA * bruto + (1 - EMA_ALPHA) * elevFiltrada;
  return elevFiltrada;
}

float inclinacaoGraus() {
  if (!imuOk) return 0;
  sensors_event_t a, g, t;
  imu.getEvent(&a, &g, &t);
  float norma = sqrtf(a.acceleration.x * a.acceleration.x + a.acceleration.y * a.acceleration.y +
                      a.acceleration.z * a.acceleration.z);
  if (norma < 0.1f) return 0;
  return acosf(fabsf(a.acceleration.z) / norma) * 180.0f / PI;
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_BTN, INPUT_PULLUP);
  pinMode(PIN_LED, OUTPUT);
  balanca.begin(PIN_HX_DT, PIN_HX_SCK);
  balanca.set_scale(HX_SCALE);
  balanca.tare();
  imuOk = imu.begin();
  Serial.println(F("{\"boot\":\"CLIP-01 TAG 3D\",\"modo\":\"M1:FORCA\"}"));
}

void loop() {
  // BTN MODO LED (borda de descida)
  bool btn = digitalRead(PIN_BTN);
  if (btnAnterior == HIGH && btn == LOW) led = !led;
  btnAnterior = btn;
  digitalWrite(PIN_LED, led ? HIGH : LOW);

  float kgf = balanca.is_ready() ? fabsf(balanca.get_units(3)) : 0;
  pico = fmaxf(pico * 0.995f, kgf);  // pico com decaimento lento (janela ~15 min no app)

  // Z_cão = (Elevação_sensor − GoogleElev(lat,lng)) × 100, projetado na vertical pela IMU
  float z = (lerElevacaoSensor() - GOOGLE_ELEV) * 100.0f * cosf(inclinacaoGraus() * PI / 180.0f);

  int uA = led ? 34 : 14;  // meta de consumo médio por modo

  Serial.printf("{\"dog\":%d,\"kgf\":%.1f,\"n\":%d,\"faixa\":\"%s\",\"z_cm\":%.1f,\"pk\":%.1f,\"led\":%d,\"uA\":%d}\n",
                DOG_ID, kgf, (int)lroundf(kgf * KGF_TO_N), faixa(kgf), z, pico, led ? 1 : 0, uA);
  delay(1000);
}
