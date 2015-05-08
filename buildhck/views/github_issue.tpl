% if subject:
[buildhck] Automated build failed
% else:
![platform icon]({{build['systemimage']}}) **{{build['system']}}** on **{{build['client']}}**
{{build['branch']}} @ {{build['commit']}}
% if build['description']:
{{build['description'].splitlines()[0]}}
% end
{{build['fdate']}} UTC
% itr = 0
% for status in STUSKEYS:
[{{status}}]({{build['url'][itr]}}) {{build['status'][itr]}}
% itr += 1
% end
% end

% # vim: set ts=8 sw=3 tw=0 :
