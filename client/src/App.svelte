<script>
  import FileList from "./components/FileList.svelte";

  const documents = [
    {
      "createdTime": "2025-08-07T17:24:26.726Z",
      "id": "1aRtvpOGGvW-FiwhrLQ7VYcmsyN5UI6yBDCFffUc7I-U",
      "lastModifyingUser": {
        "displayName": "Xinyu Zhang",
        "emailAddress": "xz@fusion.new",
        "kind": "drive#user",
        "me": true,
        "permissionId": "05129666979744630922",
        "photoLink": "https://lh3.googleusercontent.com/a/ACg8ocKVxmKtqczsCZR9kLiNNfpLPii79CJNt_wok3ysX4gHcuzl0Q=s64"
      },
      "mimeType": "application/vnd.google-apps.document",
      "modifiedTime": "2025-08-07T17:24:27.798Z",
      "name": "The Golden Gate’s Whisper",
      "owners": [
        {
          "displayName": "Xinyu Zhang",
          "emailAddress": "xz@fusion.new",
          "kind": "drive#user",
          "me": true,
          "permissionId": "05129666979744630922",
          "photoLink": "https://lh3.googleusercontent.com/a/ACg8ocKVxmKtqczsCZR9kLiNNfpLPii79CJNt_wok3ysX4gHcuzl0Q=s64"
        }
      ],
      "permissions": [
        {
          "deleted": false,
          "displayName": "Xinyu Zhang",
          "emailAddress": "xz@fusion.new",
          "id": "05129666979744630922",
          "kind": "drive#permission",
          "pendingOwner": false,
          "photoLink": "https://lh3.googleusercontent.com/a/ACg8ocKVxmKtqczsCZR9kLiNNfpLPii79CJNt_wok3ysX4gHcuzl0Q=s64",
          "role": "owner",
          "type": "user"
        }
      ],
      "shared": false,
      "size": "1701",
      "starred": false,
      "trashed": false,
      "webViewLink": "https://docs.google.com/document/d/1aRtvpOGGvW-FiwhrLQ7VYcmsyN5UI6yBDCFffUc7I-U/edit?usp=drivesdk"
    }
  ];
</script>

<FileList documents={documents} />