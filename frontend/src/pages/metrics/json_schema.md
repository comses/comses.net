The syntax is based on [yup](https://github.com/jquense/yup).

let metrics_data = object({
    members_by_year :  array(
        object({
            year : number().max(4),
            total : number(),
            full_members : number()
        })
    ),

    codebases_by_year : array(
        object({
            year : number().max(4),
            total : number(),
            peer_reviewed : number(),
            netlogo : number(),
            python : number(),
            julia : number(),
            c : number()
        })
    ),

    downloads_by_year : array(
        object({
            year : number().max(4),
            total : number()
        })
    )
})
