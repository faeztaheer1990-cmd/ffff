// Read-only MT5 bridge. This EA contains no trade execution functions.
#property strict
#property version "1.00"
input string ApiUrl="https://company-api-production-28eb7e05.up.railway.app/api/mt5/tick";
input string ApiToken="PASTE_TOKEN_IN_EA_INPUTS";
input string Symbols="XAUUSD,NAS100,EURUSD";
input int SendIntervalSeconds=5;
string symbol_list[];
int OnInit(){
 if(ApiToken=="" || ApiToken=="PASTE_TOKEN_IN_EA_INPUTS"){Print("Set API token in EA inputs.");return INIT_PARAMETERS_INCORRECT;}
 int n=StringSplit(Symbols,',',symbol_list); if(n<=0)return INIT_FAILED;
 for(int i=0;i<n;i++){StringTrimLeft(symbol_list[i]);StringTrimRight(symbol_list[i]);SymbolSelect(symbol_list[i],true);}
 EventSetTimer(MathMax(1,SendIntervalSeconds));Print("Read-only bridge active; no trading functions.");return INIT_SUCCEEDED;
}
void OnDeinit(const int reason){EventKillTimer();}
void OnTimer(){for(int i=0;i<ArraySize(symbol_list);i++){MqlTick t;if(SymbolInfoTick(symbol_list[i],t)&&t.bid>0&&t.ask>0)SendTick(symbol_list[i],t);}}
void SendTick(const string symbol,const MqlTick &t){
 string body=StringFormat("{\"symbol\":\"%s\",\"bid\":%.10f,\"ask\":%.10f,\"time\":%I64d}",symbol,t.bid,t.ask,(long)t.time);
 char data[];int len=StringToCharArray(body,data,0,WHOLE_ARRAY,CP_UTF8);if(len>0)ArrayResize(data,len-1);
 char result[];string headers="Content-Type: application/json\r\nAuthorization: Bearer "+ApiToken+"\r\n";string response_headers;
 ResetLastError();int code=WebRequest("POST",ApiUrl,headers,5000,data,result,response_headers);
 if(code==-1)Print("WebRequest error ",GetLastError(),"; allow the API host in MT5 Options > Expert Advisors.");
 else if(code!=200)Print("API HTTP ",code,": ",CharArrayToString(result));
}