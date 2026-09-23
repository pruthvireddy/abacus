# Evidence bundles

Imported historical runs preserve their original study IDs, run IDs, reports, tables, figures, and run manifests. Additive `import_manifest.json` files explain migration provenance; an imported result has not been re-evaluated or promoted to a validated strategy.

For a new completed run, save frozen config/input lock, metrics and tables, figures, HTML/Markdown report, dated advice, and a manifest with code/environment/input identities and artifact checksums. Stage work elsewhere and publish to a unique run ID only after verification. Never overwrite a completed run. See `templates/` for the artifact convention.
