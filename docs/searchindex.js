Search.setIndex({docnames:["batch_client","cli_parser","client","constants","exceptions","helpers","index","models"],envversion:{"sphinx.domains.c":2,"sphinx.domains.changeset":1,"sphinx.domains.citation":1,"sphinx.domains.cpp":4,"sphinx.domains.index":1,"sphinx.domains.javascript":2,"sphinx.domains.math":2,"sphinx.domains.python":3,"sphinx.domains.rst":2,"sphinx.domains.std":2,"sphinx.ext.viewcode":1,sphinx:56},filenames:["batch_client.rst","cli_parser.rst","client.rst","constants.rst","exceptions.rst","helpers.rst","index.rst","models.rst"],objects:{"speechmatics.batch_client":[[0,1,1,"","BatchClient"],[0,1,1,"","HttpClient"]],"speechmatics.batch_client.BatchClient":[[0,2,1,"","check_job_status"],[0,2,1,"","close"],[0,2,1,"","connect"],[0,2,1,"","delete_job"],[0,2,1,"","get_job_result"],[0,2,1,"","list_jobs"],[0,2,1,"","send_request"],[0,2,1,"","submit_job"],[0,2,1,"","wait_for_completion"]],"speechmatics.batch_client.HttpClient":[[0,2,1,"","build_request"]],"speechmatics.client":[[2,1,1,"","WebsocketClient"]],"speechmatics.client.WebsocketClient":[[2,2,1,"","add_event_handler"],[2,2,1,"","add_middleware"],[2,2,1,"","get_language_pack_info"],[2,2,1,"","run"],[2,2,1,"","run_synchronously"],[2,2,1,"","stop"],[2,2,1,"","update_transcription_config"]],"speechmatics.constants":[[3,3,1,"","BATCH_SELF_SERVICE_URL"],[3,3,1,"","RT_SELF_SERVICE_URL"]],"speechmatics.exceptions":[[4,4,1,"","EndOfTranscriptException"],[4,4,1,"","ForceEndSession"],[4,4,1,"","JobNotFoundException"],[4,4,1,"","TranscriptionError"]],"speechmatics.helpers":[[5,5,1,"","del_none"],[5,5,1,"","get_version"],[5,5,1,"","json_utf8"],[5,5,1,"","read_in_chunks"]],"speechmatics.models":[[7,1,1,"","AudioSettings"],[7,1,1,"","BatchConnectionSettings"],[7,1,1,"","BatchLanguageIdentificationConfig"],[7,1,1,"","BatchSpeakerDiarizationConfig"],[7,1,1,"","BatchTranscriptionConfig"],[7,1,1,"","BatchTranslationConfig"],[7,1,1,"","ClientMessageType"],[7,1,1,"","ConnectionSettings"],[7,1,1,"","FetchData"],[7,1,1,"","NotificationConfig"],[7,1,1,"","RTConnectionSettings"],[7,1,1,"","RTSpeakerDiarizationConfig"],[7,1,1,"","RTTranslationConfig"],[7,1,1,"","SRTOverrides"],[7,1,1,"","SentimentAnalysisConfig"],[7,1,1,"","ServerMessageType"],[7,1,1,"","SummarizationConfig"],[7,1,1,"","TopicDetectionConfig"],[7,1,1,"","TranscriptionConfig"],[7,1,1,"","TranslationConfig"],[7,1,1,"","UsageMode"],[7,1,1,"","_TranscriptionConfig"]],"speechmatics.models.AudioSettings":[[7,6,1,"","chunk_size"],[7,6,1,"","encoding"],[7,6,1,"","sample_rate"]],"speechmatics.models.BatchLanguageIdentificationConfig":[[7,6,1,"","expected_languages"]],"speechmatics.models.BatchSpeakerDiarizationConfig":[[7,6,1,"","speaker_sensitivity"]],"speechmatics.models.BatchTranscriptionConfig":[[7,6,1,"","channel_diarization_labels"],[7,6,1,"","fetch_data"],[7,6,1,"","language_identification_config"],[7,6,1,"","notification_config"],[7,6,1,"","sentiment_analysis_config"],[7,6,1,"","speaker_diarization_config"],[7,6,1,"","srt_overrides"],[7,6,1,"","summarization_config"],[7,6,1,"","topic_detection_config"],[7,6,1,"","translation_config"]],"speechmatics.models.ClientMessageType":[[7,6,1,"","AddAudio"],[7,6,1,"","EndOfStream"],[7,6,1,"","SetRecognitionConfig"],[7,6,1,"","StartRecognition"]],"speechmatics.models.ConnectionSettings":[[7,6,1,"","auth_token"],[7,6,1,"","generate_temp_token"],[7,6,1,"","message_buffer_size"],[7,6,1,"","ping_timeout_seconds"],[7,6,1,"","semaphore_timeout_seconds"],[7,6,1,"","ssl_context"],[7,6,1,"","url"]],"speechmatics.models.FetchData":[[7,6,1,"","auth_headers"],[7,6,1,"","url"]],"speechmatics.models.NotificationConfig":[[7,6,1,"","auth_headers"],[7,6,1,"","contents"],[7,6,1,"","method"],[7,6,1,"","url"]],"speechmatics.models.RTSpeakerDiarizationConfig":[[7,6,1,"","max_speakers"]],"speechmatics.models.RTTranslationConfig":[[7,6,1,"","enable_partials"]],"speechmatics.models.SRTOverrides":[[7,6,1,"","max_line_length"],[7,6,1,"","max_lines"]],"speechmatics.models.ServerMessageType":[[7,6,1,"","AddPartialTranscript"],[7,6,1,"","AddPartialTranslation"],[7,6,1,"","AddTranscript"],[7,6,1,"","AddTranslation"],[7,6,1,"","AudioAdded"],[7,6,1,"","EndOfTranscript"],[7,6,1,"","Error"],[7,6,1,"","Info"],[7,6,1,"","RecognitionStarted"],[7,6,1,"","Warning"]],"speechmatics.models.SummarizationConfig":[[7,6,1,"","content_type"],[7,6,1,"","summary_length"],[7,6,1,"","summary_type"]],"speechmatics.models.TopicDetectionConfig":[[7,6,1,"","topics"]],"speechmatics.models.TranscriptionConfig":[[7,6,1,"","ctrl"],[7,6,1,"","enable_partials"],[7,6,1,"","enable_transcription_partials"],[7,6,1,"","enable_translation_partials"],[7,6,1,"","max_delay"],[7,6,1,"","max_delay_mode"],[7,6,1,"","speaker_change_sensitivity"],[7,6,1,"","speaker_diarization_config"],[7,6,1,"","streaming_mode"],[7,6,1,"","translation_config"]],"speechmatics.models.TranslationConfig":[[7,6,1,"","target_languages"]],"speechmatics.models._TranscriptionConfig":[[7,6,1,"","additional_vocab"],[7,2,1,"","asdict"],[7,6,1,"","diarization"],[7,6,1,"","domain"],[7,6,1,"","enable_entities"],[7,6,1,"","language"],[7,6,1,"","operating_point"],[7,6,1,"","output_locale"],[7,6,1,"","punctuation_overrides"]],speechmatics:[[0,0,0,"-","batch_client"],[2,0,0,"-","client"],[3,0,0,"-","constants"],[4,0,0,"-","exceptions"],[5,0,0,"-","helpers"],[7,0,0,"-","models"]]},objnames:{"0":["py","module","Python module"],"1":["py","class","Python class"],"2":["py","method","Python method"],"3":["py","data","Python data"],"4":["py","exception","Python exception"],"5":["py","function","Python function"],"6":["py","attribute","Python attribute"]},objtypes:{"0":"py:module","1":"py:class","2":"py:method","3":"py:data","4":"py:exception","5":"py:function","6":"py:attribute"},terms:{"0":[0,1,7],"1":[1,7],"100":[0,1],"12":1,"120":7,"168":1,"192":1,"2":[1,7],"20":1,"37":7,"404":0,"4096":[1,2,7],"44100":[1,2,7],"5":1,"512":[1,7],"5646":7,"60":7,"639":[1,7],"7":[0,1],"8":1,"9000":[1,2],"boolean":2,"byte":[0,1,5,7],"case":5,"class":[0,1,2,7],"default":[0,1],"final":[1,7],"float":7,"function":[2,5],"import":6,"int":[5,7],"new":2,"return":[0,1,2,5,7],"true":[0,1,6],"while":[1,7],A:[2,5,7],FOR:1,For:[0,2],If:[1,2],It:0,The:[0,1,2,3,6,7],With:1,_transcriptionconfig:7,about:1,accept:[0,1,7],access:6,account:1,accur:1,acknowledg:7,acoust:[1,7],ad:[2,3,7],add:[0,1,2,6,7],add_event_handl:[2,6],add_middlewar:2,addaudio:[2,7],addit:[1,7],additional_vocab:[1,7],addpartialtranscript:[6,7],addpartialtransl:7,addtranscript:[2,6,7],addtransl:7,advanc:[0,1,7],after:7,afterward:0,alia:0,all:[0,1,2,5,7],allow:[1,7],also:0,alter:2,an:[0,1,2,4,6,7],analysi:[1,7],ani:[0,2,7],anymor:1,api:[0,1,2,3,6],appli:1,applianc:[0,1],ar:[0,1,2,5,7],arg:[0,2],argument:[0,2,6],around:0,as_config:7,asdict:7,asr:[0,1,2,3],associ:0,async:[2,5],asynchron:2,asyncio:2,asynciter:5,attach:7,au:7,audio:[0,1,2,5,6,7],audio_file_path:6,audio_set:2,audioad:7,audioset:[2,6,7],auth:[1,7],auth_head:7,auth_token:[0,1,6,7],authent:[1,7],author:[1,7],auto:[1,7],automat:[1,7],avail:[3,7],base:[2,7],base_url:0,batch:[0,3,6,7],batch_client:6,batch_self_service_url:3,batch_url:1,batchclient:0,batchconnectionset:7,batchlanguageidentificationconfig:7,batchspeakerdiarizationconfig:7,batchtranscriptionconfig:[0,7],batchtranslationconfig:7,bearer:7,becom:7,been:[2,7],befor:1,begin:2,being:[2,6],below:6,best:2,between:7,binari:2,block:[0,2],bool:[0,2,7],both:[1,7],boundari:7,brief:[1,7],buffer:[1,7],buffer_s:1,build:0,build_request:0,bullet:[1,7],call:2,callabl:2,callback:[2,7],caller:2,can:[1,2,4,7],cancel:0,certif:1,chang:[1,5,7],channel:[1,7],channel_and_speaker_chang:1,channel_diarization_label:[1,7],charact:7,check:0,check_job_statu:0,choic:1,chunk:[1,5,7],chunk_siz:[1,2,5,7],clean:0,cli:6,client:[0,1,6,7],clientmessagetyp:7,close:0,code:[1,7],collect:5,com:[1,3,6],comma:1,command:[2,7],compat:1,complet:[0,7],computation:1,conf:6,config:[0,2,7],config_fil:1,configur:[0,1,2,7],confirm:7,conjunct:2,connect:[0,2,7],connection_set:2,connection_settings_or_auth_token:[0,2],connection_url:6,connectionset:[0,2,6,7],consol:1,constant:3,consum:2,content:[1,7],content_typ:7,context:[0,1,7],convers:[1,7],cooki:0,copi:2,count:7,creat:[0,1,6],ctrl:[1,7],custom:[1,3,7],dai:[0,1],data:[1,2,5,7],de:1,debug:1,decor:5,def:6,defin:[6,7],del_non:5,delai:[1,7],delet:[0,5],delete_job:0,detail:[1,7],detect:[1,7],determin:[1,7],diariz:[1,7],dict:[0,2,5,7],dictionari:5,differ:1,directli:0,doc:2,doe:0,doesn:3,domain:[1,7],don:2,e:[0,1,2,7],each:[1,5],earli:4,eg:[1,7],en:[1,2,6,7],enabl:[1,7],enable_ent:7,enable_parti:[6,7],enable_transcription_parti:7,enable_translation_parti:7,encod:[1,2,7],encodingof:1,end:[2,3,4,7],endofstream:7,endoftranscript:7,endoftranscriptexcept:4,endpoint:[0,7],enforc:[1,7],engin:[1,7],enhanc:1,enterpris:[1,3,7],entiti:[1,7],entri:5,environ:1,error:[0,4,7],eu2:[3,6],event:[2,4,6],event_handl:[2,6],event_nam:[2,6],everi:2,exampl:[1,2,7],exceed:[2,7],except:[0,2,6],exclud:7,exist:0,expect:[1,7],expected_languag:7,expens:1,expliticli:0,expos:2,f:6,factori:7,fail:0,fals:[0,1,2,7],fetch:7,fetch_data:7,fetch_url:0,fetchdata:7,field:2,file:[0,1,2,5,6,7],filenam:0,filepath:1,financ:[1,7],finish:[2,4,7],first:2,fix:[1,7],flag:[1,7],flexibl:[1,7],foracknowledg:1,forc:[0,1,4],forceendsess:4,forcefulli:2,format:[0,1,7],found:[0,4,5],fr:1,from:[1,2,4,5,7],from_cli:[0,2],full:6,func:5,g:[0,1,7],gener:[1,7],generate_temp_token:[1,7],get:2,get_job_result:0,get_language_pack_info:2,get_vers:5,github:6,give:7,given:2,global:1,gnocchi:1,h:1,ha:[2,4,7],handl:[0,1,2],handler:[2,4,6],have:3,header:[0,7],helper:6,here:6,hertz:7,how:1,html:2,http:[0,1,2,3,7],httpclient:0,httperror:0,httpx:0,hz:1,i:2,id:[0,1,4,7],identif:[1,7],ignor:7,illustr:6,immedi:7,impli:2,includ:[2,7],incom:2,incomplet:7,increas:1,index:6,indic:[1,2,4,7],info:[1,7],inform:[1,2,5,7],initi:7,input:[1,5,7],insecur:1,instanc:0,instanti:2,intend:7,interact:2,interfac:[0,2],intern:[1,7],interpret:1,inth:1,invalid:0,invers:7,io:[2,5],iobas:[2,5],iso:[1,7],item:7,job:[0,4,7],job_id:[0,1],jobnotfoundexcept:[0,4],json:[0,1,5,7],json_utf8:5,just:2,kwarg:[0,2,7],label1:1,label2:1,label:[1,7],lambda:2,lang:1,langid:1,langid_expected_languag:1,languag:[1,2,3,6,7],language_identification_config:7,language_pack_info:2,larger:1,last:[0,1],latenc:1,later:1,latest:2,least:7,legaci:1,length:[1,5],level:[1,7],librari:[0,2,3,4,5,7],like:[1,2,5],line:[1,2,7],list:[0,2,7],list_job:0,list_of_job:0,liter:7,local:1,localhost:2,log:1,mai:[0,2,7],maintain:1,manag:[0,2],manifest:2,mark:[1,7],max:1,max_delai:[1,7],max_delay_mod:7,max_lin:7,max_line_length:7,max_sample_s:5,max_speak:7,maximum:[1,5,7],mean:7,merg:0,messag:[1,2,7],message_buffer_s:7,metadata:6,method:[0,5,7],middl:1,middlewar:[2,4],min:1,mode:[6,7],model:[0,1,2,6],modul:[6,7],more:[1,7],most:[2,7],msg:[2,6],much:1,mulaw:7,multipl:[1,5,7],must:0,n:7,name:[2,6,7],need:2,new_transcription_config:2,nochi:1,nokei:1,non:3,none:[0,1,2,5,7],normal:7,note:[0,3],notif:7,notification_config:7,notificationconfig:7,number:[1,5,7],oauth2:7,object:[0,2,5],one:1,onli:[1,2,7],open:[0,6],oper:1,operating_point:7,optim:7,option:[0,1,2,7],order:4,os:0,other:[0,1],out:2,outgo:2,output:[1,5,7],output_local:7,overhead:1,overrid:1,overriden:[1,7],own:[1,7],pack:[1,2,7],packag:5,page:6,paragraph:[1,7],param:0,paramet:[0,2,5,6,7],part:[6,7],partial:[1,6,7],particular:2,pass:[0,2],path:[0,6],pathlik:0,pcm_f32le:[1,7],pcm_s16le:7,per:7,perform:1,permit:[1,7],piec:1,ping:7,ping_timeout_second:7,place:5,plaintext:1,pleas:6,point:1,pong:7,pool:0,possibl:[1,2],post:7,potenti:7,pre:1,prefer:2,preset:1,previous:[0,7],print:[1,2,6],print_partial_transcript:6,print_transcript:6,probabl:2,process:[1,2],produc:[2,7],producer_consum:2,product:1,profil:1,provid:[0,1,6],puctuat:7,punctuat:[1,7],punctuation_overrid:7,punctuation_permitted_mark:1,punctuation_sensit:1,put:7,qualnam:7,queri:[0,7],rais:[0,2,4,5],rate:[1,7],rather:1,raw:[1,7],rb:6,re:[2,7],read:[1,2,5],read_in_chunk:5,readm:6,readthedoc:2,real:[1,2,7],realtim:[1,3,6],realtime_url:1,receipt:7,receiv:[1,2],recognisedent:1,recognit:[2,7],recognitionstart:[2,7],recurs:[5,7],redirect:1,refer:2,regist:6,regular:[1,7],remov:[1,7],repres:1,request:[0,1,7],requir:[0,1],respect:1,respond:2,respons:[0,7],rest:0,result:[0,2],retain:1,retriev:1,rfc:7,rt:[3,6,7],rt_self_service_url:3,rtconnectionset:7,rtspeakerdiarizationconfig:7,rttranslationconfig:7,run:[0,1,2,7],run_synchron:[2,6],s:[1,5,7],saa:[0,1],sampl:[1,7],sample_r:[1,2,7],sc:1,sdk:0,search:6,second:[2,7],section:7,see:[0,6],select:1,self:[1,3],semaphor:7,semaphore_timeout_second:7,send:[0,1,7],send_request:0,sensit:[1,7],sent:[2,7],sentenc:7,sentiment:[1,7],sentiment_analysis_config:7,sentimentanalysisconfig:7,separ:1,sequenc:5,server:[1,2,7],servermessagetyp:[2,6,7],servic:3,session:[2,4,7],set:[0,2,6,7],setrecognitionconfig:[2,7],setup:1,share:1,should:[1,2,7],show:1,sign:1,simpl:[1,2],singl:[1,7],size:[1,5,7],sm:0,small:1,sound:1,sourc:[0,2,4,5,7],space:[1,7],speaker:[1,7],speaker_chang:1,speaker_change_sensit:[1,7],speaker_diarization_config:7,speaker_diarization_max_speak:1,speaker_diarization_sensit:1,speaker_sensit:7,special:[1,7],specif:7,specifi:[1,7],speech:1,srt:[0,1,7],srt_overrid:7,srtoverrid:7,ssl:[1,7],ssl_context:7,sslcontext:7,standard:[1,7],start:7,startrecognit:7,statu:[0,7],stderr:1,stdout:1,still:0,stop:2,str:[0,2,5,7],stream:[1,2,5,7],streaming_mod:7,sub:6,submit:0,submit_job:0,subset:2,subtitl:7,successfulli:7,summar:[1,7],summari:1,summarization_config:7,summarizationconfig:7,summary_length:7,summary_typ:7,suppli:7,support:7,symbol:1,synchron:2,t:[2,3],target:7,target_languag:7,task:2,temp:1,temporari:[1,7],termin:0,text:7,than:[0,1],thei:[2,7],thi:[0,1,2,5,7],threshold:7,time:[1,2,7],timeout:[2,7],timeouterror:2,token:[1,6,7],toml:1,too:1,tool:6,topic:[1,7],topic_detection_config:7,topicdetectionconfig:7,transcrib:6,transcript:[0,1,2,4,6,7],transcription_config:[0,2],transcription_format:0,transcriptionconfig:[2,6,7],transcriptionerror:[0,4],translat:[1,7],translation_config:7,translation_target_languag:1,translationconfig:7,tupl:0,turn:5,txt:[0,1],type:[0,1,2,5,7],unbreak:1,union:[0,2],unnecessari:1,unset:0,until:[0,2,7],up:0,updat:[1,2],update_transcription_config:2,url:[0,1,2,3,6,7],us:[0,1,2,3,4,5,7],usag:1,usagemod:7,user:[1,2,4],util:5,v2:[0,1,2,3,6],v:1,valid:[0,1,2],valu:[0,1,5,7],valueerror:[2,5],variou:7,verbos:1,version:5,via:2,vocab:1,vocab_filepath:1,vocabulari:7,vv:1,wa:[1,4,5],wai:2,wait:1,wait_for_complet:0,warn:7,wav:6,waveform:6,we:[0,2,7],websocket:[1,2,7],websocketcli:[2,6],when:[0,1,2,7],where:[1,5,7],wherev:1,whether:[1,2,7],which:[0,1,2,5,7],white:7,wire:1,within:[0,1,7],word:7,work:1,would:7,wrap:7,wrapper:[0,2,6],ws:6,wss:[1,2,3,6],yet:2,yield:5,you:[0,1,2],your:[1,7]},titles:["speechmatics.batch_client","Speechmatics CLI Tool","speechmatics.client","speechmatics.client","speechmatics.exceptions","speechmatics.helpers","speechmatics-python","speechmatics.models"],titleterms:{argument:1,batch:1,batch_client:0,cli:1,client:[2,3],command:[1,6],config:1,delet:1,exampl:6,except:4,get:1,helper:5,indic:6,job:1,librari:6,line:6,list:1,mode:1,model:7,name:1,posit:1,python:6,refer:6,result:1,rt:1,set:1,speechmat:[0,1,2,3,4,5,6,7],statu:1,sub:1,submit:1,tabl:6,tool:1,transcrib:1,unset:1,usag:6}})