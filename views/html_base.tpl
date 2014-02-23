<!DOCTYPE html>
<html>
<head>
   <meta charset='UTF-8'>
   <meta name='viewport' content='width=device-width,initial-scale=1'>
   <title>{{title}}</title>
   <link rel="shortcut icon" type="image/x-icon" href="/favicon.ico"/>
   <style>
      article { display:block; }
      html { font-size:100%; -webkit-text-size-adjust:100%; -ms-text-size-adjust:100%; overflow-x:hidden; }
      body { padding:0; margin:0; font-size:12px; line-height:1.15; color:#121212; background-color:#EEE; }
      body, input { font-family: arial, sans-serif; }
      input.link, a { color:#D81860; text-decoration:none; }
      .build form, input.link { background:none; border:none; cursor:pointer; width:auto; margin:0; padding:0; display:inline; float:right; }
      a label { cursor:pointer; display:inline; }
      b, strong { font-weight:bold; }
      section.projects { margin:0 1em; }
      center.no-projects { color:#222; text-shadow: 0px 4px 3px rgba(0,0,0,0.4), 0px 8px 13px rgba(0,0,0,0.1), 0px 18px 23px rgba(0,0,0,0.1);}
      center.no-projects { position:absolute; width:100%; top:43%; font-size:80px; }
      .build { background-color:#E2E2E2; margin:12px 0; }
      .branch, .commit { color:#434343; }
      .date { color:#6E6E6E; }
      .OK { color:green; font-weight:bold; }
      .FAIL { color:#FF1300; font-weight:bold; }
      .SKIP { color:#8E8E93; font-weight:bold; }
      .col_33 { width:31%; margin:0 2% 0 0; float:left; min-width:320px; }
      .container { max-width:2048px; margin-left:auto; margin-right:auto; }
      .clearfix:before, .clearfix:after { content:""; display:table; }
      .clearfix:after { clear:both; }
      .clearfix { zoom:1; }
      @media only screen and (max-width:1100px) { .col_33 { width:100%; float:none; } }
   </style>
</head>
<body>
<div class='container'>
<section class='projects'>
{{!base}}
</section>
</div>
</body>
</html>

% # vim: set ts=8 sw=4 tw=0 ft=html :
