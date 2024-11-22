//
//  CreatePostCollectionViewCell.swift
//  A3
//
//  Created by Vin Bui on 10/31/23.
//

import UIKit

class CreatePostCollectionViewCell: UICollectionViewCell {

    // MARK: - Properties (view)

    private let postButton = UIButton()
    private let textField = UITextField()

    // MARK: - Properties (data)

    static let reuse: String = "CreatePostCollectionViewCellReuse"

    // MARK: - init

    override init(frame: CGRect) {
        super.init(frame: frame)

        backgroundColor = UIColor.a3.white
        layer.cornerRadius = 16

        setupTextField()
        setupPostButton()
    }

    required init?(coder: NSCoder) {
        fatalError("init(coder:) has not been implemented")
    }

    // MARK: - Set Up Views

    private func setupTextField() {
        textField.placeholder = "✏️ What's on your mind?"
        textField.font = .systemFont(ofSize: 16)

        contentView.addSubview(textField)
        textField.translatesAutoresizingMaskIntoConstraints = false

        let sidePadding: CGFloat = 5
        NSLayoutConstraint.activate([
            textField.leadingAnchor.constraint(equalTo: contentView.leadingAnchor, constant: sidePadding),
            textField.trailingAnchor.constraint(equalTo: contentView.trailingAnchor, constant: -sidePadding),
            textField.topAnchor.constraint(equalTo: contentView.topAnchor, constant: sidePadding)
        ])
    }

    private func setupPostButton() {
        postButton.backgroundColor = UIColor.a3.ruby
        postButton.layer.cornerRadius = 4
        postButton.setTitle("Post", for: .normal)
        postButton.setTitleColor(UIColor.a3.white, for: .normal)
        postButton.titleLabel?.font = .systemFont(ofSize: 14, weight: .semibold)
        postButton.addTarget(self, action: #selector(createPost), for: .touchUpInside)

        contentView.addSubview(postButton)
        postButton.translatesAutoresizingMaskIntoConstraints = false

        let sidePadding: CGFloat = 24
        NSLayoutConstraint.activate([
            postButton.trailingAnchor.constraint(equalTo: contentView.trailingAnchor, constant: -sidePadding),
            postButton.bottomAnchor.constraint(equalTo: contentView.bottomAnchor, constant: -sidePadding),
            postButton.widthAnchor.constraint(equalToConstant: 96),
            postButton.heightAnchor.constraint(equalToConstant: 32),
            postButton.topAnchor.constraint(equalTo: textField.bottomAnchor, constant: 32)
        ])
    }

    // MARK: - Button Helpers

    @objc private func createPost() {
        guard let message = textField.text, !message.isEmpty,
                  let url = URL(string: "https://yourapi.com/posts") else {
                print("Invalid input or URL")
                return
            }

            var request = URLRequest(url: url)
            request.httpMethod = "POST"
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            request.httpBody = try? JSONSerialization.data(withJSONObject: ["message": message])

            URLSession.shared.dataTask(with: request) { _, response, error in
                guard error == nil, let httpResponse = response as? HTTPURLResponse, (200...299).contains(httpResponse.statusCode) else {
                    print("Failed to create post")
                    return
                }
                
                DispatchQueue.main.async {
                    self.textField.text = ""
                    print("Post created successfully")
                }
            }.resume()
    }

}
