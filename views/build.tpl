% if standalone:
% rebase('html_base.tpl', title='buildhck :: {} - {}'.format(build['project'], build['system']), maxwidth=1024)
<h2><a href="{{build['upstream']}}">{{build['project']}} - {{build['system']}}</a></h2>
% end

% if standalone:
<a href='/'>index</a>
<a style='float:right;' href='/'>index</a>
% end

<div class='build'>
   <img style="float:right;" src="{{build['statusimage']}}" alt="status"/>
   <img src="{{build['systemimage']}}" alt="platform"/>
   <strong>{{build['system']}}</strong> on <strong>{{build['client']}}</strong><br/>
   <label class='branch'>{{build['branch']}}</label> @ <label class='commit'>{{build['commit']}}</label><br/>
   % if build['description']:
      {{build['description'].splitlines()[0]}}<br/>
   % end
   <label class='date'>{{build['date']}} UTC</label><br/>

   % itr = 0
   % for status in STUSKEYS:
      % css_class = 'SKIP' if status == 'analyze' else build[status]['result']
      <a href="{{build[status]['url']}}">{{status}}
      <label class="{{css_class}}">{{build[status]['result']}}</label></a>
      % itr += 1
   % end

   % if not standalone and 'history' in build:
   <a style='float:right;' href="{{'/build/{}/{}/{}'.format(build['project'], build['branch'], build['system'])}}">+</a>
   % elif admin:
   <a style='float:right;' href="{{'/delete/{}/{}/{}/{}'.format(build['project'], build['branch'], build['system'], build['fsdate'])}}">delete</a>
   % end
</div>

% if standalone and 'history' in build:
% for old in build['history']:
%    include('build.tpl', build=old, standalone=False)
% end
% end

% if standalone:
<a href='/'>index</a>
<a style='float:right;' href='/'>index</a>
% end

% # vim: set ts=8 sw=3 tw=0 :
