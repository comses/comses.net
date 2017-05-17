export interface NullWithId {
    id?: number
}

export interface User {
    username: string,
    last_name: string,
    first_name: string
}

export interface Job extends NullWithId {
    submitter?: User
    title: string
    description: string
    summary: string
    tags: Array<{name: string}>
}

export interface CalendarEvent extends NullWithId {
    submitter?: User
    title: string
    description: string
    summary: string
    tags: Array<string>
    location: string
    early_registration_deadline: string
    submission_deadline: string
    start_date: string
    end_date: string
}

export interface MemberProfile extends NullWithId {
        date_joined: string
        given_name: string
        family_name: string
        username: string

        follower_count: number
        following_count: number

        codebases: Array<Codebase>

        bio: string,
        degrees: Array<string>,
        full_member: boolean,
        institution_name: string
        institution_url: string
        keywords: Array<{name: string}>
        orcid: string
        orcid_url: string
        personal_url: string
        picture: string
        professional_url: string
        profile_url: string
        research_interests: string
    };

export interface Codebase extends NullWithId {
    title: string
    description: string

    live: boolean
    is_replication: boolean
    doi: string | null

    keywords: Array<string>

    repository_url: string
    contributors: Array<string>

}

export interface Dependency {
    identifier: string,
    name: string,
    version: string,
    os: string,
    url: string
}

export interface CodebaseRelease extends NullWithId {
    doi: string | null,
    dependencies: Array<Dependency>
    licence: string,
    description: string,
    documentation: string,
    version_number: string,
    os: string,
    platforms: Array<string>,
    programming_languages: Array<string>,
    codebase: number,
    bagit_url: string,
    git_path: string,
    submitter: User
}