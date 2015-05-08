<div class='project col_33'>
   % if 'url' in project and project['url']:
   <h2><a href="{{project['url']}}">{{project['name']}}</a></h2>
   % else:
   <h2>{{project['name']}}</h2>
   % end

   % for build in project['builds']:
   %    include('build.tpl', admin=admin, build=build, standalone=False)
   % end
</div>

% # vim: set ts=8 sw=3 tw=0 :
