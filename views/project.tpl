<div class='project col_33'>
   <h2>{{project['name']}}</h2>
   % for build in project['builds']:
   %    include('build.tpl', admin=admin, build=build, standalone=False)
   % end
</div>

% # vim: set ts=8 sw=3 tw=0 :
