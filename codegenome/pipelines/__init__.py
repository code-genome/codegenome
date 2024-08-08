def get_pipeline_by_version(gene_version, **kwargs):
    if gene_version == "genes_v0_0_1":
        from .retdecsigmal import RetdecSigmalV1

        return RetdecSigmalV1(**kwargs)
