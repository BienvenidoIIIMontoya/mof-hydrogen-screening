#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-$HOME/raspa_runs/H2_in_MOF}"
OUT_CSV="$ROOT/ALL_corrected_summary_with_sanity.csv"
MOLAR_MASS_H2="2.01588"

cases=(PS_high PS_low TPS_low)

# Keyed by "MOF|CASE"
declare -A output_file sim_file run_file
declare -A molkg mgg density ratio ratio_flag wt_pct gL fugacity compressibility bulk_fluid_density token
declare -A swap_move_pct add_acc_count add_acc_pct del_acc_count del_acc_pct generic_accepted
declare -A run_raspa_dir forcefield moleculedefinitions component_moleculedefinition eos_lines

declare -a mofs=()

calc_expr() {
  awk -v expr="$1" 'BEGIN{printf "%s", expr+0}'
}

calc_ratio() {
  awk -v mg="$1" -v mol="$2" -v mm="$MOLAR_MASS_H2" 'BEGIN{if(mol=="" || mol+0==0){print ""} else {printf "%.6f", mg/(mol*mm)}}'
}

calc_wt_pct() {
  awk -v mol="$1" -v mm="$MOLAR_MASS_H2" 'BEGIN{if(mol==""){print ""} else {printf "%.6f", (mol*mm)/10.0}}'
}

calc_gL() {
  awk -v mol="$1" -v rho="$2" -v mm="$MOLAR_MASS_H2" 'BEGIN{if(mol=="" || rho==""){print ""} else {printf "%.6f", (mol*rho*mm)/1000.0}}'
}

calc_diff() {
  awk -v a="$1" -v b="$2" 'BEGIN{if(a=="" || b==""){print ""} else {printf "%.6f", a-b}}'
}

ratio_status() {
  awk -v r="$1" 'BEGIN{if(r==""){print "MISSING"} else {d=r-1.0; if(d<0)d=-d; if(d>0.02) print "FLAG"; else print "OK"}}'
}

extract_output_fields() {
  local f="$1"
  awk '
    BEGIN{mode=""}
    {
      if(match($0,/Average loading absolute \[mol\/kg framework\][[:space:]]+([-+0-9.eE]+)/,m)) mol=m[1]
      if(match($0,/Average loading absolute \[milligram\/gram framework\][[:space:]]+([-+0-9.eE]+)/,m)) mg=m[1]
      if(match($0,/Framework Density:[[:space:]]+([-+0-9.eE]+)/,m) && dens=="") dens=m[1]
      if(match($0,/Fugacity coefficient:[[:space:]]+([-+0-9.eE]+)/,m) && fug=="") fug=m[1]
      if(match($0,/Compressibility:[[:space:]]+([-+0-9.eE]+)/,m) && z=="") z=m[1]
      if(match($0,/Density of the bulk fluid phase:[[:space:]]+([-+0-9.eE]+)/,m) && bulk=="") bulk=m[1]
      if(match($0,/atom:[[:space:]]+[0-9]+[[:space:]]+is of type:[^[]*\[([[:space:]]*[A-Za-z0-9_+\-]+)[[:space:]]*\]/,m) && tok==""){
        tok=m[1]
        gsub(/^[[:space:]]+|[[:space:]]+$/,"",tok)
      }
      if(match($0,/Percentage of swap \(insert\/delete\) moves:[[:space:]]+([-+0-9.eE]+)/,m) && swappct=="") swappct=m[1]
      if($0 ~ /Performance of the swap addition move:/){mode="add"; next}
      if($0 ~ /Performance of the swap deletion move:/){mode="del"; next}
      if(mode=="add" && $0 ~ /accepted:/){
        if(match($0,/accepted:[[:space:]]*([-+0-9.eE]+)[[:space:]]*\(([0-9.eE+\-]+)[[:space:]]*\[%\]\)/,m)){
          addacc=m[1]; addpct=m[2]; mode=""
        }
      }
      if(mode=="del" && $0 ~ /accepted:/){
        if(match($0,/accepted:[[:space:]]*([-+0-9.eE]+)[[:space:]]*\(([0-9.eE+\-]+)[[:space:]]*\[%\]\)/,m)){
          delacc=m[1]; delpct=m[2]; mode=""
        }
      }
      if($0 ~ /^[[:space:]]*accepted[[:space:]]+/ && generic==""){
        generic=$0
        gsub(/^[[:space:]]+/,"",generic)
      }
    }
    END{
      printf "%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s\n", mol,mg,dens,fug,z,bulk,tok,swappct,addacc,addpct,delacc,delpct,generic
    }
  ' "$f"
}

extract_sim_fields() {
  local f="$1"
  local ff md cmd eos
  ff=$(awk '$1=="ForceField"{print $2; exit}' "$f")
  md=$(awk '$1=="MoleculeDefinitions"{print $2; exit}' "$f")
  cmd=$(awk '$1=="MoleculeDefinition"{print $2; exit}' "$f")
  eos=$(rg -N "UseFugacityCoefficients|FugacityCoefficient|EquationOfState" "$f" | paste -sd ';' - || true)
  printf "%s|%s|%s|%s\n" "$ff" "$md" "$cmd" "$eos"
}

extract_run_raspa() {
  local f="$1"
  awk '
    /RASPA_DIR[[:space:]]*=/{
      line=$0
      sub(/^.*RASPA_DIR[[:space:]]*=[[:space:]]*/, "", line)
      gsub(/["\x27]/, "", line)
      print line
      exit
    }
  ' "$f"
}

for mofdir in "$ROOT"/*_H2; do
  [[ -d "$mofdir" ]] || continue
  mof="$(basename "$mofdir")"
  mof="${mof%_H2}"
  mofs+=("$mof")

  for case in "${cases[@]}"; do
    newest="$(find "$mofdir" -type f -path "*/Output/System_0/output_*.data" -printf '%T@|%p\n' | awk -F'|' -v c="/$case/" '$2 ~ c {if($1>mx){mx=$1;fp=$2}} END{print fp}')"
    key="$mof|$case"

    if [[ -z "$newest" ]]; then
      continue
    fi

    casedir="${newest%/Output/System_0/*}"
    sfile="$casedir/simulation.input"
    rfile="$casedir/run.sh"

    output_file[$key]="$newest"
    sim_file[$key]="$sfile"
    run_file[$key]="$rfile"

    parsed="$(extract_output_fields "$newest")"
    IFS='|' read -r mol mg dens fug z bulk tok swappct addacc addpct delacc delpct genacc <<< "$parsed"

    molkg[$key]="$mol"
    mgg[$key]="$mg"
    density[$key]="$dens"
    fugacity[$key]="$fug"
    compressibility[$key]="$z"
    bulk_fluid_density[$key]="$bulk"
    token[$key]="$tok"
    swap_move_pct[$key]="$swappct"
    add_acc_count[$key]="$addacc"
    add_acc_pct[$key]="$addpct"
    del_acc_count[$key]="$delacc"
    del_acc_pct[$key]="$delpct"
    generic_accepted[$key]="$genacc"

    ratio[$key]="$(calc_ratio "$mg" "$mol")"
    ratio_flag[$key]="$(ratio_status "${ratio[$key]}")"
    wt_pct[$key]="$(calc_wt_pct "$mol")"
    gL[$key]="$(calc_gL "$mol" "$dens")"

    if [[ -f "$sfile" ]]; then
      simparsed="$(extract_sim_fields "$sfile")"
      IFS='|' read -r ff md cmd eos <<< "$simparsed"
      forcefield[$key]="$ff"
      moleculedefinitions[$key]="$md"
      component_moleculedefinition[$key]="$cmd"
      eos_lines[$key]="$eos"
    fi

    if [[ -f "$rfile" ]]; then
      run_raspa_dir[$key]="$(extract_run_raspa "$rfile")"
    fi
  done
done

{
  printf 'MOF,'
  for case in "${cases[@]}"; do
    printf '%s_output_data,%s_simulation_input,%s_run_sh,%s_run_raspa_dir,%s_forcefield,%s_moleculedefinitions,%s_component_moleculedefinition,%s_eos_lines,%s_pseudo_atom_token,%s_molkg_abs,%s_mgg_abs,%s_framework_density_kg_m3,%s_ratio_mgg_over_molkgx2.01588,%s_ratio_flag,%s_wt_pct,%s_g_per_L,%s_fugacity_coefficient,%s_compressibility,%s_bulk_fluid_density_kg_m3,%s_swap_move_pct,%s_add_accepted_count,%s_add_accepted_pct,%s_del_accepted_count,%s_del_accepted_pct,%s_generic_accepted_line,' "$case" "$case" "$case" "$case" "$case" "$case" "$case" "$case" "$case" "$case" "$case" "$case" "$case" "$case" "$case" "$case" "$case" "$case" "$case" "$case" "$case" "$case" "$case" "$case" "$case"
  done
  printf 'UG_PS_wt_pct,UV_PS_g_L,UG_TPS_wt_pct,UV_TPS_g_L\n'

  for mof in "${mofs[@]}"; do
    printf '%s,' "$mof"

    for case in "${cases[@]}"; do
      key="$mof|$case"
      printf '%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,' \
        "${output_file[$key]-}" "${sim_file[$key]-}" "${run_file[$key]-}" "${run_raspa_dir[$key]-}" \
        "${forcefield[$key]-}" "${moleculedefinitions[$key]-}" "${component_moleculedefinition[$key]-}" "${eos_lines[$key]-}" \
        "${token[$key]-}" "${molkg[$key]-}" "${mgg[$key]-}" "${density[$key]-}" "${ratio[$key]-}" "${ratio_flag[$key]-}" \
        "${wt_pct[$key]-}" "${gL[$key]-}" "${fugacity[$key]-}" "${compressibility[$key]-}" "${bulk_fluid_density[$key]-}" \
        "${swap_move_pct[$key]-}" "${add_acc_count[$key]-}" "${add_acc_pct[$key]-}" "${del_acc_count[$key]-}" "${del_acc_pct[$key]-}" "${generic_accepted[$key]-}"
    done

    ug_ps="$(calc_diff "${wt_pct[$mof|PS_high]-}" "${wt_pct[$mof|PS_low]-}")"
    uv_ps="$(calc_diff "${gL[$mof|PS_high]-}" "${gL[$mof|PS_low]-}")"
    ug_tps="$(calc_diff "${wt_pct[$mof|PS_high]-}" "${wt_pct[$mof|TPS_low]-}")"
    uv_tps="$(calc_diff "${gL[$mof|PS_high]-}" "${gL[$mof|TPS_low]-}")"

    printf '%s,%s,%s,%s\n' "$ug_ps" "$uv_ps" "$ug_tps" "$uv_tps"
  done
} > "$OUT_CSV"

# Stable ordering by MOF while keeping header first.
{
  head -n 1 "$OUT_CSV"
  tail -n +2 "$OUT_CSV" | sort -t, -k1,1
} > "$OUT_CSV.tmp"
mv "$OUT_CSV.tmp" "$OUT_CSV"

printf 'Wrote %s\n' "$OUT_CSV"
