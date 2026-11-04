# 组员交付：C_黄祉玥_Q3

- 组员：C 黄祉玥
- 覆盖问题：Q3 温度/降水异常与疫情强度
- 来源压缩包：`组员分析任务交接\NOAA_气象分析.zip`（原件保留，此为解压合并副本）
- 合并日期：2026-11-03（E 侧重构项目层级时解压入库）

## 内容清单

  Q3_NOAA_20261031/
    README.md
    requirements-lock.txt
    requirements.txt
    .mplconfig/
      fontlist-v3.11.0.json
    analysis/
      noaa_source_card/
        NOAA_source_card.md
        补充材料/
          collection_record.md
          coverage_by_city.csv
          field_dictionary.csv
          raw_coverage_by_city.csv
          raw_file_manifest.csv
          raw_station_city_mapping.csv
          raw_weekly_comparison.csv
          station_city_mapping.csv
          unit_sample_comparison.csv
      q3/
        Q3_one_page.html
        Q3_report.md
        analysis_input.csv
        city_correlations.csv
        correlations.csv
        q3_city_comparison.png
        q3_core.png
        补充材料/
          analysis_input.csv
          city_correlations.csv
          inherited_newspaper_denominator_audit.csv
          q3_core.svg
          reproducibility_check.json
          run_manifest.json
          sensitivity.csv
          sensitivity_comparison.csv
          sensitivity_summary.csv
          smoothing_counts.csv
          tycho_non_sunday_audit.csv
          verification.json
    data/
      integrated/
        weekly_sixcities_1915_1922_1930_1932.csv
    docs/
      AI_USAGE_C.md
      GAPS.md
    scripts/
      audit_noaa_raw.py
      build_integrated.py
      build_noaa_source_card.py
      organize_analysis.py
      package_delivery.py
      run_q3.py
      verify_reproducibility.py
      .idea/
        .gitignore
        dbnavigator.xml
        misc.xml
        modules.xml
        scripts.iml
        workspace.xml
        inspectionProfiles/
          profiles_settings.xml
