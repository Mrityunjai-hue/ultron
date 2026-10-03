/*
 * ULTRON Arduino UNO R4 Wifi — Minimal Companion Brain
 * ═══════════════════════════════════════════════════════
 * 
 * Architecture (concise fit for embedded):
 *   State machine: IDLE → LISTEN → THINK → SPEAK → IDLE
 *   LED Matrix: 8x8 mood patterns
 *   Serial: Receives commands from laptop/USB host
 *   WiFi:   Optional cloud LLM or local Ollama bridge
 * 
 * Hardware:
 *   - Arduino UNO R4 Wifi (onboard LED matrix 8x12)
 *   - USB Serial for I/O
 *   - WiFi for optional Ollama bridge
 */

#include "Arduino_LED_Matrix.h"
#include <WiFiS3.h>
#include <ArduinoJson.h>

// ── State Machine ───────────────────────────────────── //
enum UltronState : uint8_t {
  IDLE = 0, LISTEN, THINK, SPEAK, RESPONSE, ALERT, SLEEP
};
UltronState currentState = IDLE;
UltronState prevState    = IDLE;
unsigned long stateStart = 0;

// ── LED Matrix ──────────────────────────────────────── //
ArduinoLEDMatrix matrix;

// LED patterns (8x12 = 96 bits, stored as 3×uint32_t)
// Patterns: pulse dots for each state
const uint32_t PATTERN_IDLE[3]   = {0x000C00, 0x000000, 0x000C00}; // 2 dots (breathing)
const uint32_t PATTERN_LISTEN[3] = {0x3C3C3C, 0x000000, 0x3C3C3C}; // ring
const uint32_t PATTERN_THINK[3]  = {0x183C7E, 0x7E3C18, 0x000000}; // hourglass
const uint32_t PATTERN_SPEAK[3]  = {0x3C4242, 0x423C00, 0x000000}; // wave
const uint32_t PATTERN_ALERT[3]  = {0xFFFFFF, 0xFFFFFF, 0xFFFFFF}; // all on
const uint32_t PATTERN_SLEEP[3]  = {0x000000, 0x001800, 0x000000}; // single dot

// ── System ─────────────────────────────────────────── //
String inputBuffer = "";
bool serialReady   = false;
unsigned long lastHeartbeat = 0;
uint8_t animFrame = 0;
unsigned long lastAnimTick = 0;

// ── WiFi Config (optional) ─────────────────────────── //
// #define WIFI_SSID "your_ssid"
// #define WIFI_PASS "your_pass"
// #define OLLAMA_HOST "192.168.1.x"
// #define OLLAMA_PORT 11434

// ════════════════════════════════════════════════════ //
void setup() {
  Serial.begin(115200);
  while (!Serial && millis() < 3000);

  matrix.begin();
  matrix.loadFrame(PATTERN_IDLE);

  // Optional WiFi
  // WiFi.begin(WIFI_SSID, WIFI_PASS);

  setState(IDLE);
  Serial.println("{\"type\":\"boot\",\"status\":\"ULTRON_READY\"}");
}

// ════════════════════════════════════════════════════ //
void loop() {
  handleSerial();
  updateAnimation();
  checkStateTimeout();
}

// ── Serial Command Handler ─────────────────────────── //
void handleSerial() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n') {
      processCommand(inputBuffer.trim());
      inputBuffer = "";
    } else {
      inputBuffer += c;
    }
  }
}

void processCommand(String cmd) {
  // Expect JSON: {"type":"setState","state":"listening"}
  // or simple text: "STATE:LISTEN", "SPEAK:Hello world"
  if (cmd.startsWith("{")) {
    StaticJsonDocument<256> doc;
    if (deserializeJson(doc, cmd) == DeserializationError::Ok) {
      const char* type = doc["type"];
      if (strcmp(type, "setState") == 0) {
        String s = doc["state"].as<String>();
        setStateFromString(s);
      } else if (strcmp(type, "speak") == 0) {
        // Could drive PWM audio or serial-pass to laptop speaker
        setState(SPEAK);
      }
    }
  } else if (cmd.startsWith("STATE:")) {
    setStateFromString(cmd.substring(6));
  } else if (cmd.startsWith("WAKE")) {
    setState(LISTEN);
    sendEvent("wakeword_detected");
  }
}

void setStateFromString(String s) {
  s.toLowerCase();
  if      (s == "idle")        setState(IDLE);
  else if (s == "listening")   setState(LISTEN);
  else if (s == "thinking" ||
           s == "processing")  setState(THINK);
  else if (s == "speaking")    setState(SPEAK);
  else if (s == "response")    setState(RESPONSE);
  else if (s == "alert" ||
           s == "error")       setState(ALERT);
  else if (s == "sleep")       setState(SLEEP);
}

// ── State Machine ───────────────────────────────────── //
void setState(UltronState next) {
  prevState  = currentState;
  currentState = next;
  stateStart = millis();
  animFrame  = 0;
  loadPattern(next);
  sendStateEvent(next);
}

void loadPattern(UltronState s) {
  switch(s) {
    case IDLE:     matrix.loadFrame(PATTERN_IDLE);     break;
    case LISTEN:   matrix.loadFrame(PATTERN_LISTEN);   break;
    case THINK:    matrix.loadFrame(PATTERN_THINK);    break;
    case SPEAK:    matrix.loadFrame(PATTERN_SPEAK);    break;
    case RESPONSE: matrix.loadFrame(PATTERN_IDLE);     break;
    case ALERT:    matrix.loadFrame(PATTERN_ALERT);    break;
    case SLEEP:    matrix.loadFrame(PATTERN_SLEEP);    break;
  }
}

void checkStateTimeout() {
  unsigned long elapsed = millis() - stateStart;
  switch(currentState) {
    case LISTEN:    if (elapsed > 8000) setState(IDLE);     break;
    case THINK:     if (elapsed > 10000) setState(ALERT);   break;
    case SPEAK:     if (elapsed > 15000) setState(IDLE);    break;
    case RESPONSE:  if (elapsed > 3000)  setState(IDLE);    break;
    case ALERT:     if (elapsed > 5000)  setState(IDLE);    break;
    default: break;
  }
}

// ── Animation Tick ──────────────────────────────────── //
void updateAnimation() {
  unsigned long now = millis();
  uint16_t tickMs = 500; // default tick

  switch(currentState) {
    case IDLE:   tickMs = 1000; break;
    case LISTEN: tickMs = 200;  break;
    case THINK:  tickMs = 400;  break;
    case SPEAK:  tickMs = 150;  break;
    default:     tickMs = 500;  break;
  }

  if (now - lastAnimTick >= tickMs) {
    lastAnimTick = now;
    animFrame = (animFrame + 1) % 4;
    // Could cycle through sub-frames here for animation
    // For now, single-frame patterns are loaded at state entry
  }

  // Heartbeat LED blink (built-in LED)
  if (now - lastHeartbeat >= 2000) {
    lastHeartbeat = now;
    digitalWrite(LED_BUILTIN, HIGH);
    delay(80);
    digitalWrite(LED_BUILTIN, LOW);
  }
}

// ── Serial Events ───────────────────────────────────── //
void sendEvent(const char* eventType) {
  Serial.print("{\"type\":\"event\",\"event\":\"");
  Serial.print(eventType);
  Serial.println("\"}");
}

void sendStateEvent(UltronState s) {
  const char* names[] = {"idle","listening","thinking","speaking","response","alert","sleep"};
  Serial.print("{\"type\":\"stateChange\",\"state\":\"");
  Serial.print(names[s]);
  Serial.println("\"}");
}
