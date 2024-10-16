#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <WiFiClientSecureBearSSL.h>
#include <SPI.h>
#include <WiFiClientSecure.h>
#include <MFRC522.h>

const char* ssid = "PocoX6Pro5g";             // Nome da sua rede Wi-Fi
const char* password = "politaogostoso";        // Senha da rede
const char* serverUrl = "https://apigrafica.onrender.com/sensor_data/";  // URL da API com HTTPS
const char* pingUrl = "https://apigrafica.onrender.com/ping";  // URL para o ping

#define RST_PIN D1  // Pino de reset do RC522
#define SS_PIN  D2  // Pino de seleção do slave (SDA)

MFRC522 mfrc522(SS_PIN, RST_PIN);  // Cria uma instância do MFRC522

unsigned long lastPingTime = 0;  // Armazena o último horário do ping
const unsigned long pingInterval = 30000;  // Intervalo de ping em milissegundos (30 segundos)

void setup() {
  Serial.begin(115200);

  // Inicializa o SPI e o leitor RC522
  SPI.begin();          
  mfrc522.PCD_Init();   
  Serial.println("Leitor RFID inicializado.");

  // Conectar ao Wi-Fi
  WiFi.begin(ssid, password);
  Serial.print("Conectando ao Wi-Fi");
  
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nWi-Fi conectado!");
  Serial.print("Endereço IP: ");
  Serial.println(WiFi.localIP());

  // Envia o primeiro ping assim que conectar
  sendPing();
}

void loop() {
  // Verifica se deve enviar o ping
  unsigned long currentMillis = millis();
  if (currentMillis - lastPingTime >= pingInterval) {
    sendPing();
    lastPingTime = currentMillis;  // Atualiza o tempo do último ping
  }

  // Verifica se um cartão está presente
  if (mfrc522.PICC_IsNewCardPresent() && mfrc522.PICC_ReadCardSerial()) {
    // Lê o ID do cartão
    String rfid = "";
    for (byte i = 0; i < mfrc522.uid.size; i++) {
      rfid += String(mfrc522.uid.uidByte[i], HEX);
    }
    
    // Exibe o ID lido no Monitor Serial
    Serial.print("RFID lido: ");
    Serial.println(rfid);

    // Envia o JSON para a API
    sendJsonToApi(rfid);
    
    // Aguarda o final da leitura do cartão
    mfrc522.PICC_HaltA();
    delay(1000);  // Aguarda um pouco antes de ler o próximo cartão
  }
}

// Função para enviar um ping para a API
void sendPing() {
  if (WiFi.status() == WL_CONNECTED) {
    WiFiClientSecure client;  // Cria uma instância do WiFiClientSecure
    HTTPClient http;

    // Desabilitar verificação de certificado (não recomendado em produção)
    client.setInsecure(); 

    Serial.println("Enviando ping...");
    http.begin(client, pingUrl);  // Inicia a conexão com a URL do ping
    int httpResponseCode = http.GET();  // Envia a requisição GET

    // Verifica a resposta do ping
    if (httpResponseCode > 0) {
      String response = http.getString();  // Obtém a resposta da API
      Serial.print("Ping resposta: ");
      Serial.println(response);
    } else {
      Serial.print("Erro na requisição de ping: ");
      Serial.println(httpResponseCode);
      Serial.println(http.errorToString(httpResponseCode));  // Mensagem de erro detalhada
    }

    http.end();  // Fecha a conexão HTTP
  } else {
    Serial.println("Wi-Fi desconectado");
  }
}

// Função para enviar o JSON via HTTPS POST
void sendJsonToApi(String rfid) {
  if (WiFi.status() == WL_CONNECTED) {  // Verifica se está conectado ao Wi-Fi
    std::unique_ptr<BearSSL::WiFiClientSecure> client(new BearSSL::WiFiClientSecure);

    // Opcional: Desabilita a verificação de certificado (não recomendado em produção)
    client->setInsecure();

    HTTPClient http;
    http.begin(*client, serverUrl);  // Inicia a conexão HTTPS com a URL
    http.addHeader("Content-Type", "application/json");  // Define o tipo do conteúdo

    // Define o JSON a ser enviado
    String json = "{\"rfid\": \"" + rfid + "\"}";

    // Envia a requisição POST
    int httpResponseCode = http.POST(json);

    // Verifica a resposta da API
    if (httpResponseCode > 0) {
      String response = http.getString();  // Obtém a resposta da API
      Serial.print("Resposta da API: ");
      Serial.println(response);
    } else {
      Serial.print("Erro na requisição HTTPS: ");
      Serial.println(httpResponseCode);
    }

    http.end();  // Fecha a conexão HTTP
  } else {
    Serial.println("Wi-Fi desconectado");
  }
}
