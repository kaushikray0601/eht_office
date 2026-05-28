# Comprehensive Vendor Research Plan
**Date**: 2026-05-29
**Objective**: Collect complete SR cable catalogue from vendor websites

## Vendors to Research (Priority Order)

### Priority 1: New Vendors (Currently Only 3 Records Each)
1. **Heat Trace** - Currently: 3 records (PowerHeat series only)
   - Search for: PH series, Plus series, other SR heating cables
   - Website: heattrace.com
   - Expected additional models

2. **Eltherm** - Currently: 3 records (FSH series only)
   - Search for: FSH series, other self-regulating models
   - Website: eltherm.de or eltherm.com
   - Expected additional models

3. **Pentair Raychem** - Currently: 3 records (ACE series only)
   - Search for: ACE series, HCT series, other SR models
   - Website: raychem.pentair.com
   - Expected additional models

### Priority 2: Existing Vendors with Limited Coverage
4. **nVent** - Currently: 77 records (8 SR + 69 MI)
   - Should research: More SR series beyond BTV/QTVR
   - Website: nvent.com
   - May have: QTV, other constant wattage SR series

5. **Thermon** - Currently: 31 records (9 SR + 22 MI)
   - Should research: VSX, HTSX, and other SR series variants
   - Website: thermon.com
   - May have: More power ratings or series variants

6. **Chromalox** - Currently: 6 records (All SR)
   - Should research: SRM series variants, other SR models
   - Website: chromalox.com
   - May have: More power ratings

7. **SST** - Currently: 10 records (All SR)
   - Should research: BTC, BTX series variants
   - Website: sst-heating.com
   - May have: More models or power ratings

### Priority 3: Existing Vendors with Good Coverage
8. **Krus-Zapad** - Currently: 103 records
   - Should verify: If all available models are in database
   - Website: krus-zapad.com

## Data Collection Strategy

For each vendor, collect:
- Cable model/series name
- Voltage rating
- Power ratings available
- Temperature ratings (Maint_T, Max_Op_T, etc.)
- Hazardous area classifications (Zone, Gas_Group, T_Rating)
- Resistance characteristics (if available)
- Electrical specifications

## Storage Plan
- Temporary CSV file: `/home/kr/mydev/eht_office/RESEARCH_DATA/vendor_research_[vendor_name].csv`
- Master research file: `/home/kr/mydev/eht_office/RESEARCH_DATA/ALL_VENDORS_RESEARCH.csv`
- Will compare with database before adding

## Validation Checklist
- [ ] Heat Trace - Research complete
- [ ] Eltherm - Research complete
- [ ] Pentair - Research complete
- [ ] nVent - Additional models research complete
- [ ] Thermon - Additional models research complete
- [ ] Chromalox - Additional models research complete
- [ ] SST - Additional models research complete
- [ ] Temporary CSV created with all new data
- [ ] Compared with existing database
- [ ] Identified unique records
- [ ] Data format validated against model
- [ ] Safe import script created
- [ ] Imported without data corruption
