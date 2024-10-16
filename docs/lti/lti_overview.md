# LTI Overview

LTI (Learning Tools Interoperability) is a standard developed by the IMS Global Learning Consortium for integrating external learning tools with educational platforms like Learning Management Systems (LMS). It allows educational institutions to connect various tools and services with their LMS in a seamless and standardized manner, facilitating the sharing of resources, assignments, and grades.

LTI 1.3 is the latest version of this standard and the one currently being implemented on KinesinLMS. LTI 1.3 enhances the integration experience with improved security and functionality.

Implementation is currently in progress and the feature is in an alpha state. These pages will be filled out with more information as work progresses.

## LTI1.3 Platform URLs

KinesinLMS serves as an LTI "Platform." The following URLs on KinesinLMS are significant when setting up external tools:

- Keyset URL: `https://(your kinesinLMS domain)/lti/security/jwks/`
- Platform Callback URL: `https://(your kinesinLMS domain)/lti/authorize_redirect/`

## ExternalTool Setup  

External tools are configured in KinesinLMS by:

- creating an "External Tool Provider" in the Management tab to represent the external tool.
- creating an "External Tool View" block in composer wherever you want this tool to appear in a course.

## ExternalTool Provider

To configure an external tool in KinesinLMS, you'll need some basic LTI1.3 information from the tool. These
bits of data are standard things needed by LTI1.3 for smooth communication between the platform and tool.

- Login URL: this is the first tool URL the platform uses when launching a tool. It's a 'pre-flight' URL that establishing a connection and asks the tool to start the OIDC login process with the platform.
- Launch URI: this is the tool URL that KinesinLMS will direct the user to once the login was successful between the tool and KinesinLMS.
- Public Keyset URL: this is the tool URL where the tool's public keyset is made available. (This is only necessary for an extended version of LTIv1.3 that KinesinLMS does not support yet.)
- Client ID: This is an ID that KinesinLMS associates with the tool.
- Deployment ID: This is an ID for the "deployment" of the tool in Kinesin. Currently this is fixed to '1' as multiple deployments are not supported yet.

You'll need to go configure the external tool with whatever values are shown for client ID and deployment ID.
