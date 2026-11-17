// Read-only MT5 bridge. No trade execution functions.
#property strict
#property version "1.02"

input string ApiUrl = "https://company-api-production-28eb7e05.up.railway.app/api/mt5/tick";
input string ApiToken = "PASTE_TOKEN_IN_EA_INPUTS";
input string Symbols = "XAUUSD,NAS100,EURUSD";
input int SendIntervalSeconds = 5;

string symbol_list[];

void SendTick(const string symbol, const MqlTick &tick);

int OnInit()
{
   if(ApiToken == "" || ApiToken == "PASTE_TOKEN_IN_EA_INPUTS")
   {
      Print("Set the API token in the EA inputs before running.");
      return INIT_PARAMETERS_INCORRECT;
   }

   int count = StringSplit(Symbols, ',', symbol_list);
   if(count <= 0)
      return INIT_FAILED;

   for(int i = 0; i < count; i++)
   {
      StringTrimLeft(symbol_list[i]);
      StringTrimRight(symbol_list[i]);
      if(!SymbolSelect(symbol_list[i], true))
         Print("Could not select symbol: ", symbol_list[i]);
   }

   EventSetTimer(MathMax(1, SendIntervalSeconds));
   Print("Read-only bridge initialized. No trades will be placed.");
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   EventKillTimer();
}

void OnTimer()
{
   for(int i = 0; i < ArraySize(symbol_list); i++)
   {
      MqlTick tick;
      if(SymbolInfoTick(symbol_list[i], tick) && tick.bid > 0 && tick.ask > 0)
         SendTick(symbol_list[i], tick);
   }
}

void SendTick(const string symbol, const MqlTick &tick)
{
   string body = StringFormat(
      "{\"symbol\":\"%s\",\"bid\":%.10f,\"ask\":%.10f,\"time\":%I64d}",
      symbol, tick.bid, tick.ask, (long)tick.time
   );

   char data[];
   int length = StringToCharArray(body, data, 0, WHOLE_ARRAY, CP_UTF8);
   if(length > 0)
      ArrayResize(data, length - 1);

   char result[];
   string response_headers;
   string headers = "Content-Type: application/json\r\nAuthorization: Bearer " + ApiToken + "\r\n";

   ResetLastError();
   int http_code = WebRequest(
      "POST", ApiUrl, headers, 5000, data, result, response_headers
   );

   if(http_code == -1)
      Print("WebRequest failed. Error: ", GetLastError());
   else if(http_code < 200 || http_code >= 300)
      Print("API HTTP error: ", http_code, " Response: ", CharArrayToString(result));
}