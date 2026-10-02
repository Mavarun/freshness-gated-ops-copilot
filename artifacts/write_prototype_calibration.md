# Write-prototype backoff calibration (dev verbs only)

51 hand-written dev verbs (22 with an action, 29 reads / unsupported / nonsense), none in a write lexicon or the held-out list. Backend: `frozen`.

Chosen: threshold **0.73**, margin **0.07** (feasible with a 0.02 buffer; optimal threshold run [0.5, 0.73], the strictest end taken); 10 of 22 dev positives accepted with the right action, 0 negatives accepted, 0 wrong actions.

| verb | kind | label | nearest | cosine | margin | accepted |
| --- | --- | --- | --- | ---: | ---: | --- |
| reload | service | restart_service | restart_service | 0.886 | 0.083 | yes |
| rerun | service | restart_service | restart_service | 0.850 | 0.069 | no |
| refresh | service | restart_service | restart_service | 0.818 | 0.096 | yes |
| upscale | service | scale_service | scale_service | 0.734 | 0.161 | yes |
| expand | service | scale_service | scale_service | 0.738 | 0.050 | no |
| shrink | service | scale_service | scale_service | 0.748 | 0.077 | yes |
| resize | service | scale_service | scale_service | 0.773 | 0.175 | yes |
| restore | service | rollback_deploy | rollback_deploy | 0.832 | 0.052 | no |
| downgrade | service | rollback_deploy | rollback_deploy | 0.788 | 0.069 | no |
| launch | service | deploy_release | READ | 0.749 | 0.004 | no |
| publish | service | deploy_release | deploy_release | 0.753 | 0.077 | yes |
| summon | recipient | page_oncall | READ | 0.759 | 0.007 | no |
| call | recipient | page_oncall | READ | 0.831 | 0.013 | no |
| wake | recipient | page_oncall | UNSUPPORTED | 0.762 | 0.003 | no |
| activate | flag | toggle_flag | toggle_flag | 0.878 | 0.088 | yes |
| deactivate | flag | toggle_flag | toggle_flag | 0.882 | 0.029 | no |
| reroll | secret | rotate_secret | rotate_secret | 0.765 | 0.037 | no |
| replace | secret | rotate_secret | UNSUPPORTED | 0.895 | 0.043 | no |
| tweak | config_key | patch_config | patch_config | 0.898 | 0.094 | yes |
| alter | config_key | patch_config | patch_config | 0.944 | 0.119 | yes |
| amend | config_key | patch_config | patch_config | 0.874 | 0.149 | yes |
| empty | cache | clear_cache | UNSUPPORTED | 0.869 | 0.060 | no |
| trace | service | none | READ | 0.840 | 0.195 | no |
| audit | service | none | READ | 0.797 | 0.188 | no |
| grep | service | none | READ | 0.720 | 0.040 | no |
| tail | service | none | UNSUPPORTED | 0.713 | 0.055 | no |
| query | service | none | READ | 0.697 | 0.112 | no |
| profile | service | none | READ | 0.706 | 0.105 | no |
| curl | service | none | READ | 0.553 | 0.032 | no |
| ssh | service | none | READ | 0.581 | 0.059 | no |
| view | service | none | READ | 0.858 | 0.188 | no |
| analyze | service | none | READ | 0.815 | 0.165 | no |
| test | service | none | READ | 0.751 | 0.135 | no |
| debug | service | none | READ | 0.801 | 0.182 | no |
| open | service | none | deploy_release | 0.759 | 0.034 | no |
| nuke | service | none | UNSUPPORTED | 0.777 | 0.085 | no |
| zap | service | none | UNSUPPORTED | 0.662 | 0.009 | no |
| scrap | service | none | UNSUPPORTED | 0.848 | 0.057 | no |
| obliterate | service | none | UNSUPPORTED | 0.872 | 0.073 | no |
| isolate | service | none | UNSUPPORTED | 0.742 | 0.084 | no |
| love | service | none | READ | 0.678 | 0.053 | no |
| thank | service | none | READ | 0.598 | 0.059 | no |
| praise | flag | none | READ | 0.689 | 0.012 | no |
| read | secret | none | READ | 0.837 | 0.074 | no |
| copy | secret | none | UNSUPPORTED | 0.776 | 0.019 | no |
| share | secret | none | READ | 0.845 | 0.061 | no |
| leak | secret | none | UNSUPPORTED | 0.854 | 0.016 | no |
| export | config_key | none | READ | 0.678 | 0.026 | no |
| screenshot | config_key | none | READ | 0.746 | 0.017 | no |
| thank | recipient | none | READ | 0.682 | 0.092 | no |
| email | recipient | none | page_oncall | 0.805 | 0.045 | no |
