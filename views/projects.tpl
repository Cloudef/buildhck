% rebase('html_base.tpl', title='buildhck')

% if not projects:
<center class='no-projects'>No Projects</center>
% end

% itr = 0
% for project in projects:
%    include('project.tpl', admin=admin, project=project)
%    itr += 1
%    if itr >= 3:
        <div class='clearfix'></div>
%       itr = 0
%    end
% end

% # vim: set ts=8 sw=4 tw=0 ft=html :
