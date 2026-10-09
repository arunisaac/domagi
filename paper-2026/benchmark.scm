(define odgi-build
  (command #:inputs (tool #:type string) graph (threads #:type int)
           #:run "time" "${ var prefix='--format={\"metrics\": \"build %e %U %S %M\", \"odgi-graph\": {\"class\": \"File\", \"path\": \"'; var suffix='\"}}'; switch (inputs.tool) { case \"odgi\": return prefix + inputs.graph.nameroot + '.og' + suffix; case \"domagi\": return prefix + inputs.graph.nameroot + '.db' + suffix; }}" "--output=cwl.output.json" tool "build" ("-t" threads) ("-g" graph) ("-o" "${switch (inputs.tool) { case \"odgi\": return inputs.graph.nameroot + \".og\"; case \"domagi\": return inputs.graph.nameroot + \".db\";}}")
           #:outputs (metrics #:type string) (odgi-graph #:binding ((glob . "${switch (inputs.tool) { case \"odgi\": return inputs.graph.nameroot + \".og\"; case \"domagi\": return inputs.graph.nameroot + \".db\";}}")))
           #:other ((hints (ResourceRequirement
                            (coresMin . "$(inputs.threads)"))
                           (SoftwareRequirement
                            (packages . #(((package . "domagi"))
                                          ((package . "odgi"))
                                          ((package . "time")))))))))

(define odgi-paths
  (command #:inputs (tool #:type string) graph (threads #:type int)
           #:run "time" "--format={\"metrics\": \"paths %e %U %S %M\"}" "--output=cwl.output.json" tool "paths" ("-t" threads) ("-i" graph) "--list-paths"
	   #:outputs (metrics #:type string)
           #:other ((hints (ResourceRequirement
                            (coresMin . "$(inputs.threads)"))
                           (SoftwareRequirement
                            (packages . #(((package . "domagi"))
                                          ((package . "odgi"))
                                          ((package . "time")))))))))

(define odgi-crush
  (command #:inputs (tool #:type string) graph (threads #:type int)
           #:run "time" "--format={\"metrics\": \"crush %e %U %S %M\"}" "--output=cwl.output.json" tool "crush" ("-t" threads) ("-i" graph) ("-o" "${switch (inputs.tool) { case \"odgi\": return inputs.graph.nameroot + \".og\"; case \"domagi\": return inputs.graph.nameroot + \".db\";}}")
	   #:outputs (metrics #:type string)
           #:other ((hints (ResourceRequirement
                            (coresMin . "$(inputs.threads)"))
                           (SoftwareRequirement
                            (packages . #(((package . "domagi"))
                                          ((package . "odgi"))
                                          ((package . "time")))))))))

(define odgi-depth
  (command #:inputs (tool #:type string) graph (threads #:type int)
           #:run "time" "--format={\"metrics\": \"depth %e %U %S %M\"}" "--output=cwl.output.json" tool "depth" ("-t" threads) ("-i" graph)
	   #:outputs (metrics #:type string)
           #:other ((hints (ResourceRequirement
                            (coresMin . "$(inputs.threads)"))
                           (SoftwareRequirement
                            (packages . #(((package . "domagi"))
                                          ((package . "odgi"))
                                          ((package . "time")))))))))

(define odgi-depth-graph-depth-table
  (command #:inputs (tool #:type string) graph (threads #:type int)
           #:run "time" "--format={\"metrics\": \"depth-table %e %U %S %M\"}" "--output=cwl.output.json" tool "depth" ("-t" threads) ("-i" graph) "--graph-depth-table"
	   #:outputs (metrics #:type string)
           #:other ((hints (ResourceRequirement
                            (coresMin . "$(inputs.threads)"))
                           (SoftwareRequirement
                            (packages . #(((package . "domagi"))
                                          ((package . "odgi"))
                                          ((package . "time")))))))))

(define odgi-matrix
  (command #:inputs (tool #:type string) graph (threads #:type int)
           #:run "time" "--format={\"metrics\": \"matrix %e %U %S %M\"}" "--output=cwl.output.json" tool "matrix" ("-t" threads) ("-i" graph)
	   #:outputs (metrics #:type string)
           #:other ((hints (ResourceRequirement
                            (coresMin . "$(inputs.threads)"))
                           (SoftwareRequirement
                            (packages . #(((package . "domagi"))
                                          ((package . "odgi"))
                                          ((package . "time")))))))))

(define odgi-stats
  (command #:inputs (tool #:type string) graph (threads #:type int)
           #:run "time" "--format={\"metrics\": \"stats %e %U %S %M\"}" "--output=cwl.output.json" tool "stats" ("-t" threads) ("-i" graph)
	   #:outputs (metrics #:type string)
           #:other ((hints (ResourceRequirement
                            (coresMin . "$(inputs.threads)"))
                           (SoftwareRequirement
                            (packages . #(((package . "domagi"))
                                          ((package . "odgi"))
                                          ((package . "time")))))))))

(define odgi-view
  (command #:inputs (tool #:type string) graph (threads #:type int)
           #:run "time" "--format={\"metrics\": \"view %e %U %S %M\"}" "--output=cwl.output.json" tool "view" ("-t" threads) ("-i" graph) "--to-gfa"
	   #:outputs (metrics #:type string)
           #:other ((hints (ResourceRequirement
                            (coresMin . "$(inputs.threads)"))
                           (SoftwareRequirement
                            (packages . #(((package . "domagi"))
                                          ((package . "odgi"))
                                          ((package . "time")))))))))

(define combine-metrics
  (command #:inputs (tool #:type string) (build_metrics #:type string) (crush_metrics #:type string) (depth_metrics #:type string) (depth_graph_depth_table_metrics #:type string) (matrix_metrics #:type string) (paths_metrics #:type string) (stats_metrics #:type string) (view_metrics #:type string)
           #:run "echo" "$([inputs.build_metrics, inputs.crush_metrics, inputs.depth_metrics, inputs.depth_graph_depth_table_metrics, inputs.matrix_metrics, inputs.paths_metrics, inputs.stats_metrics, inputs.view_metrics].join(`\n`))"
           #:outputs (metrics #:type stdout)
           #:stdout "$(inputs.tool)-metrics"
           #:other ((hints (SoftwareRequirement
                            (packages . #(((package . "coreutils")))))))))

(define benchmark-tool
  (workflow ((tool #:type string) chr8 (threads #:type int))
    (pipe (odgi-build #:tool tool
                      #:graph chr8
		      #:threads threads)
	  (rename #:build-metrics metrics)
	  (tee (identity)
               (pipe (odgi-crush #:tool tool
                                 #:graph odgi-graph
				 #:threads threads)
		     (rename #:crush-metrics metrics))
	       (pipe (odgi-depth #:tool tool
                                 #:graph odgi-graph
				 #:threads threads)
		     (rename #:depth-metrics metrics))
	       (pipe (odgi-depth-graph-depth-table #:tool tool
                                                   #:graph odgi-graph
	        			           #:threads threads)
	             (rename #:depth-graph-depth-table-metrics metrics))
               (pipe (odgi-matrix #:tool tool
                                 #:graph odgi-graph
				 #:threads threads)
		     (rename #:matrix-metrics metrics))
	       (pipe (odgi-paths #:tool tool
                                 #:graph odgi-graph
				 #:threads threads)
		     (rename #:paths-metrics metrics))
	       (pipe (odgi-stats #:tool tool
                                 #:graph odgi-graph
				 #:threads threads)
		     (rename #:stats-metrics metrics))
               (pipe (odgi-view #:tool tool
                                #:graph odgi-graph
				#:threads threads)
		     (rename #:view-metrics metrics)))
          (combine-metrics #:tool tool
                           #:build_metrics build-metrics
                           #:crush_metrics crush-metrics
                           #:depth_metrics depth-metrics
                           #:depth_graph_depth_table_metrics depth-graph-depth-table-metrics
                           #:matrix_metrics matrix-metrics
                           #:paths_metrics paths-metrics
                           #:stats_metrics stats-metrics
                           #:view_metrics view-metrics))))

(workflow ((tools #:type (array string)) chr8 (threads #:type int))
  (scatter (benchmark-tool #:chr8 chr8
                           #:threads threads)
           #:tool tools))
